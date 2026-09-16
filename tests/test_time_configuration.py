import json
from pathlib import Path
from unittest.mock import MagicMock

from pytest import MonkeyPatch

from archinstall.lib.args import ArchConfig, ArchConfigHandler, ArchConfigType, Arguments
from archinstall.lib.global_menu import GlobalMenu
from archinstall.lib.hardware import SysInfo
from archinstall.lib.installer import Installer


class FakeEfiBootManagerCommand:
	def __init__(self, output: str) -> None:
		self.output = output

	def decode(self) -> str:
		return self.output


def test_hardware_clock_setting_roundtrip() -> None:
	config = ArchConfig(hardware_clock_utc=False)
	serialized = config.safe_config()

	assert serialized[ArchConfigType.HARDWARE_CLOCK_UTC] is False
	assert ArchConfig.from_config({'hardware_clock_utc': False}, Arguments()).hardware_clock_utc is False


def test_windows_boot_manager_detection(monkeypatch) -> None:  # type: ignore[no-untyped-def]
	monkeypatch.setattr(
		'archinstall.lib.hardware.SysCommand',
		lambda command: FakeEfiBootManagerCommand('Boot0000* Windows Boot Manager\n'),
	)

	assert SysInfo.has_windows_bootloader()


def test_time_configuration_defaults_off_when_windows_is_detected(monkeypatch) -> None:  # type: ignore[no-untyped-def]
	monkeypatch.setattr(SysInfo, 'has_uefi', staticmethod(lambda: True))
	monkeypatch.setattr(SysInfo, 'has_windows_bootloader', staticmethod(lambda: True))
	config = ArchConfig()

	GlobalMenu(config)

	assert config.hardware_clock_utc is False


def test_time_configuration_preserves_saved_hardware_clock_setting(monkeypatch) -> None:  # type: ignore[no-untyped-def]
	monkeypatch.setattr(SysInfo, 'has_uefi', staticmethod(lambda: True))
	monkeypatch.setattr(SysInfo, 'has_windows_bootloader', staticmethod(lambda: True))
	config = ArchConfig(hardware_clock_utc=True)

	GlobalMenu(config)

	assert config.hardware_clock_utc is True


def test_silent_config_defaults_off_when_windows_is_detected(monkeypatch: MonkeyPatch) -> None:
	monkeypatch.setattr('sys.argv', ['archinstall', '--silent'])
	monkeypatch.setattr(SysInfo, 'has_windows_bootloader', staticmethod(lambda: True))

	handler = ArchConfigHandler()

	assert handler.config.hardware_clock_utc is False


def test_silent_config_preserves_explicit_hardware_clock_setting(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	config_file = tmp_path / 'config.json'
	config_file.write_text(json.dumps({'hardware_clock_utc': True}))

	monkeypatch.setattr('sys.argv', ['archinstall', '--silent', '--config', str(config_file)])
	monkeypatch.setattr(SysInfo, 'has_windows_bootloader', staticmethod(lambda: True))

	handler = ArchConfigHandler()

	assert handler.config.hardware_clock_utc is True


def test_set_hardware_clock_utc_runs_in_target(tmp_path: Path) -> None:
	installer = MagicMock(spec=Installer)
	installer.target = tmp_path

	Installer.set_hardware_clock_utc(installer)

	installer.arch_chroot.assert_called_once_with('hwclock --systohc --utc')
