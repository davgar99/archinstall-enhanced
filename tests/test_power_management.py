from pathlib import Path

from archinstall.applications.power_management import PowerManagementApp
from archinstall.lib.applications.application_menu import ApplicationMenu
from archinstall.lib.models.application import PowerManagement, PowerManagementConfiguration


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


def test_power_management_menu_available_without_battery_gate() -> None:
	item = ApplicationMenu()._item_group.find_by_key('power_management_config')
	assert item.enabled


def test_power_profiles_daemon_install_is_exclusive(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	PowerManagementApp().install(
		installer,  # type: ignore[arg-type]
		PowerManagementConfiguration(PowerManagement.POWER_PROFILES_DAEMON),
	)

	assert installer.packages == ['power-profiles-daemon']
	assert installer.services == ['power-profiles-daemon.service']
	assert 'tuned' not in installer.packages
	assert 'tuned-ppd' not in installer.packages


def test_tuned_install_is_exclusive(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	PowerManagementApp().install(
		installer,  # type: ignore[arg-type]
		PowerManagementConfiguration(PowerManagement.TUNED),
	)

	assert installer.packages == ['tuned', 'tuned-ppd']
	assert installer.services == ['tuned.service']
	assert 'power-profiles-daemon' not in installer.packages
