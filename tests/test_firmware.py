from pathlib import Path

from archinstall.applications.firmware import FirmwareApp
from archinstall.lib.applications.application_menu import ApplicationMenu
from archinstall.lib.models.application import ApplicationConfiguration, FirmwareConfiguration


class FakeInstaller:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.packages: list[str] = []
		self.services: list[str] = []

	def add_additional_packages(self, packages: list[str]) -> None:
		self.packages.extend(packages)

	def enable_service(self, services: list[str]) -> None:
		self.services.extend(services)


def test_firmware_install_enables_metadata_refresh(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	FirmwareApp().install(installer, FirmwareConfiguration(enabled=True))  # type: ignore[arg-type]

	assert installer.packages == ['fwupd']
	assert installer.services == ['fwupd-refresh.timer']


def test_firmware_disabled_does_not_install_packages(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	FirmwareApp().install(installer, FirmwareConfiguration(enabled=False))  # type: ignore[arg-type]

	assert installer.packages == []
	assert installer.services == []


def test_firmware_configuration_roundtrip_and_summary() -> None:
	config = ApplicationConfiguration(firmware_config=FirmwareConfiguration(enabled=True))

	assert config.json() == {'firmware_config': {'enabled': True}}
	assert ApplicationConfiguration.parse_arg({'firmware_config': {'enabled': True}}) == config
	assert config.summary() == ['Firmware updates: Enabled']


def test_firmware_menu_is_in_hardware_section() -> None:
	menu = ApplicationMenu()
	texts = [item.text for item in menu._item_group.items]

	assert texts.index('Hardware') < texts.index('Firmware updates') < texts.index('Media and appearance')
	assert menu._item_group.find_by_key('firmware_config').enabled
