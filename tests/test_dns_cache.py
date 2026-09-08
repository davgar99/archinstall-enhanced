import asyncio
from pathlib import Path

import pytest

from archinstall.lib.global_menu import GlobalMenu
from archinstall.lib.menu.helpers import Selection
from archinstall.lib.models.network import DnsResolver, MacAddressPolicy, NetworkConfiguration, NicType
from archinstall.lib.network.network_handler import install_network_config
from archinstall.lib.network.network_menu import _select_dns_resolver
from archinstall.tui.menu_item import MenuItem
from archinstall.tui.result import Result


class FakeInstaller:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.packages: list[str] = []
		self.services: list[str] = []
		self.disabled_services: list[str] = []
		self.stub_mode = False

	def add_additional_packages(self, packages: str | list[str]) -> None:
		if isinstance(packages, str):
			self.packages.append(packages)
		else:
			self.packages.extend(packages)

	def enable_service(self, services: str | list[str]) -> None:
		if isinstance(services, str):
			self.services.append(services)
		else:
			self.services.extend(services)

	def systemd_resolved_stub_mode(self) -> None:
		self.stub_mode = True

	def disable_service(self, service: str) -> None:
		self.disabled_services.append(service)


@pytest.mark.parametrize('nic_type', [NicType.NM, NicType.NM_IWD])
def test_systemd_resolved_dns_cache(tmp_path: Path, nic_type: NicType) -> None:
	installer = FakeInstaller(tmp_path)
	config = NetworkConfiguration(nic_type, dns_resolver=DnsResolver.SYSTEMD_RESOLVED)

	install_network_config(config, installer)  # type: ignore[arg-type]

	assert (tmp_path / 'etc/NetworkManager/conf.d/dns-cache.conf').read_text() == '[main]\ndns=systemd-resolved\n'
	assert (tmp_path / 'etc/systemd/resolved.conf.d/dns-cache.conf').read_text() == ('[Resolve]\nCache=yes\nDNSStubListener=yes\nMulticastDNS=resolve\n')
	assert 'systemd-resolved.service' in installer.services
	assert installer.stub_mode


def test_dnsmasq_dns_cache(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	config = NetworkConfiguration(NicType.NM, dns_resolver=DnsResolver.DNSMASQ)

	install_network_config(config, installer)  # type: ignore[arg-type]

	assert 'dnsmasq' in installer.packages
	assert (tmp_path / 'etc/NetworkManager/conf.d/dns-cache.conf').read_text() == '[main]\ndns=dnsmasq\n'
	assert (tmp_path / 'etc/NetworkManager/dnsmasq.d/cache.conf').read_text() == 'cache-size=1000\n'
	assert 'systemd-resolved.service' not in installer.services
	assert not installer.stub_mode


def test_dns_over_https_uses_dnscrypt_proxy(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	config = NetworkConfiguration(NicType.NM, dns_resolver=DnsResolver.DNS_OVER_HTTPS)

	install_network_config(config, installer)  # type: ignore[arg-type]

	assert 'dnscrypt-proxy' in installer.packages
	assert 'dnscrypt-proxy.service' in installer.services
	assert (tmp_path / 'etc/NetworkManager/conf.d/dns-cache.conf').read_text() == '[main]\ndns=none\n'
	proxy_config = (tmp_path / 'etc/dnscrypt-proxy/dnscrypt-proxy.toml').read_text()
	assert 'dnscrypt_servers = false' in proxy_config
	assert 'doh_servers = true' in proxy_config
	assert 'require_dnssec = true' in proxy_config
	assert (tmp_path / 'etc/resolv.conf').read_text().startswith('nameserver 127.0.0.1\n')


def test_dns_over_https_replaces_existing_resolver_symlink(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	etc = tmp_path / 'etc'
	etc.mkdir()
	resolved = etc / 'resolved.conf'
	resolved.write_text('keep me\n')
	(etc / 'resolv.conf').symlink_to('resolved.conf')

	install_network_config(NetworkConfiguration(NicType.NM, dns_resolver=DnsResolver.DNS_OVER_HTTPS), installer)  # type: ignore[arg-type]

	assert not (etc / 'resolv.conf').is_symlink()
	assert (etc / 'resolv.conf').read_text().startswith('nameserver 127.0.0.1\n')
	assert resolved.read_text() == 'keep me\n'


@pytest.mark.parametrize('policy', [MacAddressPolicy.STABLE, MacAddressPolicy.RANDOM])
def test_wifi_mac_privacy_policy(tmp_path: Path, policy: MacAddressPolicy) -> None:
	installer = FakeInstaller(tmp_path)
	config = NetworkConfiguration(NicType.NM, mac_address_policy=policy)

	install_network_config(config, installer)  # type: ignore[arg-type]

	assert (tmp_path / 'etc/NetworkManager/conf.d/wifi-mac-privacy.conf').read_text() == (
		f'[device]\nwifi.scan-rand-mac-address=yes\n\n[connection]\nwifi.cloned-mac-address={policy.value}\n'
	)


def test_network_privacy_configuration_round_trip() -> None:
	config = NetworkConfiguration(
		NicType.NM,
		dns_resolver=DnsResolver.DNS_OVER_HTTPS,
		mac_address_policy=MacAddressPolicy.STABLE,
	)

	assert NetworkConfiguration.parse_arg(config.json()) == config


def test_default_dns_cache_is_backward_compatible() -> None:
	assert NetworkConfiguration.parse_arg({'type': 'nm'}) == NetworkConfiguration(NicType.NM)


def test_dns_cache_is_included_in_network_summary() -> None:
	config = NetworkConfiguration(NicType.NM, dns_resolver=DnsResolver.SYSTEMD_RESOLVED)

	assert config.summary() == 'Use Network Manager (default backend)\nDNS cache: systemd-resolved'


def test_privacy_settings_are_included_in_network_summary() -> None:
	config = NetworkConfiguration(
		NicType.NM,
		dns_resolver=DnsResolver.DNS_OVER_HTTPS,
		mac_address_policy=MacAddressPolicy.STABLE,
	)

	assert config.summary() == 'Use Network Manager (default backend)\nDNS cache: dns-over-https\nWi-Fi MAC policy: stable-ssid'


def test_dns_cache_is_included_in_global_menu_preview() -> None:
	config = NetworkConfiguration(NicType.NM, dns_resolver=DnsResolver.DNSMASQ)
	item = MenuItem('Network configuration', value=config)

	preview = GlobalMenu._prev_network_config(None, item)  # type: ignore[arg-type]

	assert preview == 'Network configuration:\nUse Network Manager (default backend)\nDNS cache: dnsmasq'


def test_dns_resolver_menu_marks_recommended_and_focuses_first(monkeypatch: pytest.MonkeyPatch) -> None:
	async def select_focused(selection: Selection[DnsResolver]) -> Result[DnsResolver]:
		group = selection._group
		assert group.default_item is not None
		assert group.default_item.value == DnsResolver.SYSTEMD_RESOLVED
		first = group.get_enabled_items()[0]
		assert group.focus_item is first
		return Result.selection(first.value)

	monkeypatch.setattr(Selection, 'show', select_focused)

	assert asyncio.run(_select_dns_resolver(None)) == next(iter(DnsResolver))
