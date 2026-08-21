import textwrap

from archinstall.lib.installer import Installer
from archinstall.lib.models.network import DnsResolver, NetworkConfiguration, NicType
from archinstall.lib.models.profile import ProfileConfiguration


def install_network_config(
	network_config: NetworkConfiguration,
	installation: Installer,
	profile_config: ProfileConfiguration | None = None,
) -> None:
	match network_config.type:
		case NicType.ISO:
			# Sources the ISO network configuration to the install medium.
			installation.copy_iso_network_config(enable_services=True)
		case NicType.NM | NicType.NM_IWD:
			packages = ['networkmanager']

			if network_config.type == NicType.NM:
				packages.append('wpa_supplicant')
			else:
				packages.append('iwd')

			if profile_config and profile_config.profile:
				if profile_config.profile.is_desktop_profile():
					packages.append('network-manager-applet')

			installation.add_additional_packages(packages)
			installation.enable_service('NetworkManager.service')
			_configure_dns_cache(installation, network_config.dns_resolver)

			if network_config.type == NicType.NM_IWD:
				_configure_nm_iwd(installation)
				installation.disable_service('iwd.service')

		case NicType.IWD:
			installation.add_additional_packages(['iwd'])
			_configure_iwd_standalone(installation)
			installation.enable_service('iwd.service')
			installation.enable_service('systemd-networkd.service')
			installation.enable_service('systemd-resolved.service')

		case NicType.MANUAL:
			for nic in network_config.nics:
				installation.configure_nic(nic)
			installation.enable_service('systemd-networkd')
			installation.enable_service('systemd-resolved')


def _configure_nm_iwd(installation: Installer) -> None:
	nm_conf_dir = installation.target / 'etc/NetworkManager/conf.d'
	nm_conf_dir.mkdir(parents=True, exist_ok=True)

	iwd_backend_conf = nm_conf_dir / 'wifi_backend.conf'
	iwd_backend_conf.write_text('[device]\nwifi.backend=iwd\n')


def _configure_dns_cache(installation: Installer, resolver: DnsResolver) -> None:
	if resolver == DnsResolver.DEFAULT:
		return

	nm_conf_dir = installation.target / 'etc/NetworkManager/conf.d'
	nm_conf_dir.mkdir(parents=True, exist_ok=True)
	(nm_conf_dir / 'dns-cache.conf').write_text(f'[main]\ndns={resolver.value}\n')

	if resolver == DnsResolver.SYSTEMD_RESOLVED:
		installation.enable_service('systemd-resolved.service')
		installation.systemd_resolved_stub_mode()
		resolved_conf_dir = installation.target / 'etc/systemd/resolved.conf.d'
		resolved_conf_dir.mkdir(parents=True, exist_ok=True)
		(resolved_conf_dir / 'dns-cache.conf').write_text('[Resolve]\nCache=yes\nDNSStubListener=yes\nMulticastDNS=resolve\n')
	else:
		installation.add_additional_packages(['dnsmasq'])
		dnsmasq_dir = installation.target / 'etc/NetworkManager/dnsmasq.d'
		dnsmasq_dir.mkdir(parents=True, exist_ok=True)
		(dnsmasq_dir / 'cache.conf').write_text('cache-size=1000\n')


def _configure_iwd_standalone(installation: Installer) -> None:
	# iwd manages wireless only; systemd-networkd handles wired DHCP.
	iwd_conf_dir = installation.target / 'etc/iwd'
	iwd_conf_dir.mkdir(parents=True, exist_ok=True)

	main_conf = iwd_conf_dir / 'main.conf'
	main_conf_content = textwrap.dedent("""\
		[General]
		EnableNetworkConfiguration=true

		[Network]
		NameResolvingService=systemd
	""")
	main_conf.write_text(main_conf_content)

	networkd_dir = installation.target / 'etc/systemd/network'
	networkd_dir.mkdir(parents=True, exist_ok=True)
	wired_conf = networkd_dir / '20-wired.network'
	wired_conf_content = textwrap.dedent("""\
		[Match]
		Type=ether
		Kind=!*

		[Network]
		DHCP=yes
	""")
	wired_conf.write_text(wired_conf_content)

	installation.systemd_resolved_stub_mode()
