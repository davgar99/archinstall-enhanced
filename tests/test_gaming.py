from pathlib import Path

import pytest
from pytest import MonkeyPatch

from archinstall.applications.cpu_scheduler import CPUSchedulerApp
from archinstall.applications.gaming_tools import GamingToolsApp
from archinstall.applications.hardware_watchdog import HardwareWatchdogApp
from archinstall.applications.ntsync import NTSyncApp
from archinstall.lib.args import ArchConfig, ArchConfigType, Arguments
from archinstall.lib.gaming.gaming_menu import GamingMenu
from archinstall.lib.hardware import CPUVendor, SysInfo
from archinstall.lib.models.gaming import (
	CPU_SCHEDULER_STABILITY,
	CPUScheduler,
	CPUSchedulerConfiguration,
	CPUSchedulerStability,
	GamingConfiguration,
	NTSyncConfiguration,
)
from archinstall.lib.models.users import Password, User


class FakeInstaller:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.packages: list[str] = []
		self.services: list[str] = []
		self.chroot_commands: list[str] = []
		self.mkinitcpio_calls: list[list[str]] = []

	def add_additional_packages(self, packages: list[str]) -> None:
		self.packages.extend(packages)

	def enable_service(self, service: str) -> None:
		self.services.append(service)

	def arch_chroot(self, command: str) -> None:
		self.chroot_commands.append(command)

	def mkinitcpio(self, flags: list[str]) -> bool:
		self.mkinitcpio_calls.append(flags)
		return True


def test_cpu_scheduler_stability() -> None:
	stable = {
		CPUScheduler.BEERLAND,
		CPUScheduler.BPFLAND,
		CPUScheduler.COSMOS,
		CPUScheduler.FLASH,
		CPUScheduler.LAVD,
		CPUScheduler.P2DQ,
		CPUScheduler.PANDEMONIUM,
		CPUScheduler.RUSTLAND,
		CPUScheduler.RUSTY,
	}
	experimental = {
		CPUScheduler.CAKE,
		CPUScheduler.FLOW,
		CPUScheduler.FORGE,
		CPUScheduler.TICKLESS,
	}

	assert set(CPU_SCHEDULER_STABILITY) == set(CPUScheduler)
	assert {scheduler for scheduler in CPUScheduler if scheduler.stability() == CPUSchedulerStability.STABLE} == stable
	assert {scheduler for scheduler in CPUScheduler if scheduler.stability() == CPUSchedulerStability.EXPERIMENTAL} == experimental


def test_gaming_configuration_roundtrip() -> None:
	gaming_config = GamingConfiguration(
		cpu_scheduler_config=CPUSchedulerConfiguration(scheduler=CPUScheduler.LAVD),
		ntsync_config=NTSyncConfiguration(enabled=True),
		gamemode=True,
		mangohud=False,
		gamescope=True,
		disable_watchdog=True,
	)
	serialized = gaming_config.json()

	assert serialized == {
		'cpu_scheduler_config': {'scheduler': 'scx_lavd'},
		'ntsync_config': {'enabled': True},
		'gamemode': True,
		'mangohud': False,
		'gamescope': True,
		'disable_watchdog': True,
	}
	assert GamingConfiguration.parse_arg(serialized) == gaming_config

	arch_config = ArchConfig(gaming_config=gaming_config)
	assert arch_config.safe_config()[ArchConfigType.GAMING_CONFIG] == serialized
	assert ArchConfig.from_config({'gaming_config': serialized}, Arguments()).gaming_config == gaming_config


def test_gaming_multilib_requirement() -> None:
	assert GamingConfiguration(gamemode=True).requires_multilib()
	assert GamingConfiguration(mangohud=True).requires_multilib()
	assert not GamingConfiguration(gamescope=True).requires_multilib()
	assert not GamingConfiguration(ntsync_config=NTSyncConfiguration(enabled=True)).requires_multilib()
	assert not GamingConfiguration(disable_watchdog=True).requires_multilib()


def test_hardware_watchdog_modules() -> None:
	app = HardwareWatchdogApp()
	assert app.module(CPUVendor.AMD) == 'sp5100_tco'
	assert app.module(CPUVendor.INTEL) == 'iTCO_wdt'
	assert app.module(CPUVendor._UNKNOWN) is None


def test_hardware_watchdog_is_advanced_only() -> None:
	assert not GamingMenu(advanced=False)._item_group.find_by_key('disable_watchdog').enabled
	assert GamingMenu(advanced=True)._item_group.find_by_key('disable_watchdog').enabled


@pytest.mark.parametrize(
	('vendor', 'module'),
	[(CPUVendor.AMD, 'sp5100_tco'), (CPUVendor.INTEL, 'iTCO_wdt')],
)
def test_hardware_watchdog_disabled_for_supported_vendor(
	tmp_path: Path,
	monkeypatch: MonkeyPatch,
	vendor: CPUVendor,
	module: str,
) -> None:
	installer = FakeInstaller(tmp_path)
	monkeypatch.setattr(SysInfo, 'cpu_vendor', lambda: vendor)

	HardwareWatchdogApp().install(installer, GamingConfiguration(disable_watchdog=True))  # type: ignore[arg-type]

	assert (tmp_path / 'etc/modprobe.d/disable-watchdog.conf').read_text() == f'blacklist {module}\n'
	assert installer.mkinitcpio_calls == [['-P']]


def test_hardware_watchdog_no_selection_leaves_enabled(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	app = HardwareWatchdogApp()

	app.install(installer, GamingConfiguration(disable_watchdog=None))  # type: ignore[arg-type]
	app.install(installer, GamingConfiguration(disable_watchdog=False))  # type: ignore[arg-type]

	assert not (tmp_path / 'etc/modprobe.d/disable-watchdog.conf').exists()
	assert installer.mkinitcpio_calls == []


def test_hardware_watchdog_unsupported_vendor_skips_without_writing(
	tmp_path: Path,
	monkeypatch: MonkeyPatch,
) -> None:
	installer = FakeInstaller(tmp_path)
	monkeypatch.setattr(SysInfo, 'cpu_vendor', lambda: CPUVendor._UNKNOWN)

	HardwareWatchdogApp().install(installer, GamingConfiguration(disable_watchdog=True))  # type: ignore[arg-type]

	assert not (tmp_path / 'etc/modprobe.d/disable-watchdog.conf').exists()
	assert installer.mkinitcpio_calls == []


def test_cpu_scheduler_install(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	config = CPUSchedulerConfiguration(scheduler=CPUScheduler.LAVD)

	CPUSchedulerApp().install(installer, config)  # type: ignore[arg-type]

	assert installer.packages == ['scx-scheds', 'scx-tools']
	assert installer.services == ['scx_loader.service']
	assert (tmp_path / 'etc/scx_loader/config.toml').read_text() == 'default_sched = "scx_lavd"\ndefault_mode = "Gaming"\n'


def test_ntsync_install(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	NTSyncApp().install(installer, NTSyncConfiguration(enabled=True))  # type: ignore[arg-type]

	assert installer.packages == ['ntsync-autoload']
	assert installer.services == []


def test_ntsync_disabled_does_not_install(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	NTSyncApp().install(installer, NTSyncConfiguration(enabled=False))  # type: ignore[arg-type]

	assert installer.packages == []
	assert installer.services == []


def test_gaming_tools_install(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	config = GamingConfiguration(gamemode=True, mangohud=True, gamescope=True)
	user = User('david', Password(enc_password='test'), sudo=True)

	GamingToolsApp().install(installer, config, [user])  # type: ignore[arg-type]

	assert installer.packages == [
		'gamemode',
		'lib32-gamemode',
		'mangohud',
		'lib32-mangohud',
		'gamescope',
	]
	assert installer.chroot_commands == ['usermod -aG gamemode david']
