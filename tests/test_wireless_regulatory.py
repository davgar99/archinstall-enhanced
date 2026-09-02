from pathlib import Path
from unittest.mock import patch

from archinstall.lib.network.regulatory import configure_wireless_regulatory, country_code_for_timezone


class FakeInstaller:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.packages: list[str] = []
		self.services: list[str] = []

	def add_additional_packages(self, packages: list[str]) -> None:
		self.packages.extend(packages)

	def enable_service(self, services: str | list[str]) -> None:
		if isinstance(services, str):
			self.services.append(services)
		else:
			self.services.extend(services)


def _zone_table(tmp_path: Path) -> Path:
	table = tmp_path / 'zone1970.tab'
	table.write_text(
		'# countries\tcoordinates\ttimezone\nUS\t+404251-0740023\tAmerica/New_York\nRU\t+554521+0373704\tEurope/Moscow\nCA,BS\t+4339-07923\tAmerica/Toronto\n',
		encoding='utf-8',
	)
	return table


def test_country_code_for_timezone(tmp_path: Path) -> None:
	table = _zone_table(tmp_path)

	assert country_code_for_timezone('America/New_York', table) == 'US'
	assert country_code_for_timezone('Europe/Moscow', table) == 'RU'
	assert country_code_for_timezone('UTC', table) is None
	assert country_code_for_timezone('America/Toronto', table) is None


@patch('archinstall.lib.network.regulatory.SysInfo.has_wifi', return_value=False)
def test_skips_ethernet_only_system(has_wifi: object, tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	configure_wireless_regulatory(installer, 'America/New_York')  # type: ignore[arg-type]

	assert installer.packages == []
	assert installer.services == []
	assert not (tmp_path / 'etc/conf.d/wireless-regdom').exists()


@patch('archinstall.lib.network.regulatory.country_code_for_timezone', return_value='US')
@patch('archinstall.lib.network.regulatory.SysInfo.has_wifi', return_value=True)
def test_configures_wifi_system(has_wifi: object, country: object, tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	configure_wireless_regulatory(installer, 'America/New_York')  # type: ignore[arg-type]

	assert installer.packages == ['wireless-regdb', 'iw']
	assert installer.services == ['wireless-regdom.service', 'wireless-regdom.path']
	assert (tmp_path / 'etc/conf.d/wireless-regdom').read_text() == (
		'# Set this to an ISO 3166-1 alpha-2 country code to override timezone detection.\nWIRELESS_REGDOM=AUTO\n'
	)
	assert (tmp_path / 'usr/lib/archinstall/set-wireless-regdom').stat().st_mode & 0o111
	assert 'PathChanged=/etc/localtime' in (tmp_path / 'etc/systemd/system/wireless-regdom.path').read_text()


@patch('archinstall.lib.network.regulatory.country_code_for_timezone', return_value=None)
@patch('archinstall.lib.network.regulatory.SysInfo.has_wifi', return_value=True)
def test_ambiguous_timezone_keeps_automatic_world_domain(
	has_wifi: object,
	country: object,
	tmp_path: Path,
) -> None:
	installer = FakeInstaller(tmp_path)

	configure_wireless_regulatory(installer, 'UTC')  # type: ignore[arg-type]

	assert (tmp_path / 'etc/conf.d/wireless-regdom').read_text().endswith('WIRELESS_REGDOM=AUTO\n')


@patch('archinstall.lib.network.regulatory.SysInfo.has_wifi', return_value=True)
def test_configures_wifi_system_without_timezone(has_wifi: object, tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	configure_wireless_regulatory(installer, None)  # type: ignore[arg-type]

	assert installer.packages == ['wireless-regdb', 'iw']
	assert installer.services == ['wireless-regdom.service', 'wireless-regdom.path']
	assert (tmp_path / 'etc/conf.d/wireless-regdom').read_text().endswith('WIRELESS_REGDOM=AUTO\n')
