import asyncio
from pathlib import Path

from pytest import MonkeyPatch

from archinstall.applications.power_management import PowerManagementApp
from archinstall.lib.applications.application_menu import ApplicationMenu, select_power_management
from archinstall.lib.menu.helpers import Selection
from archinstall.lib.models.application import PowerManagement, PowerManagementConfiguration
from archinstall.tui.result import Result


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


def test_power_management_menu_marks_recommended_and_focuses_first(monkeypatch: MonkeyPatch) -> None:
	async def select_focused(selection: Selection[PowerManagement]) -> Result[PowerManagement]:
		group = selection._group
		# power-profiles-daemon stays labelled as the recommended option...
		assert group.default_item is not None
		assert group.default_item.value == PowerManagement.POWER_PROFILES_DAEMON
		# ...while the cursor starts on the first option like every other prompt.
		first = group.get_enabled_items()[0]
		assert group.focus_item is first
		return Result.selection(first.value)

	monkeypatch.setattr(Selection, 'show', select_focused)

	first_power_mgmt = next(iter(PowerManagement))
	assert asyncio.run(select_power_management()) == PowerManagementConfiguration(first_power_mgmt)


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
	assert installer.services == ['tuned.service', 'tuned-ppd.service']
	assert 'power-profiles-daemon' not in installer.packages
