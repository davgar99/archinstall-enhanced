from pathlib import Path

import pytest

from archinstall.lib.disk import luks
from archinstall.lib.exceptions import DiskError, SysCallError


class FakeCommand:
	def __init__(self, output: str) -> None:
		self.output = output

	def decode(self) -> str:
		return self.output


def test_dm_crypt_preflight_skips_modprobe_when_module_exists(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(Path, 'exists', lambda self: str(self) == '/sys/module/dm_crypt')
	monkeypatch.setattr(luks, 'SysCommand', lambda command: pytest.fail(f'unexpected command: {command}'))

	luks.ensure_dm_crypt_available()


def test_dm_crypt_preflight_loads_module(monkeypatch: pytest.MonkeyPatch) -> None:
	loaded = False

	def exists(path: Path) -> bool:
		return loaded and str(path) == '/sys/module/dm_crypt'

	def sys_command(command: str) -> None:
		nonlocal loaded
		assert command == 'modprobe dm-crypt'
		loaded = True

	monkeypatch.setattr(Path, 'exists', exists)
	monkeypatch.setattr(luks, 'SysCommand', sys_command)

	luks.ensure_dm_crypt_available()


def test_dm_crypt_preflight_reports_missing_kernel_support(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(Path, 'exists', lambda self: False)

	def fail_modprobe(command: str) -> None:
		assert command == 'modprobe dm-crypt'
		raise SysCallError('missing module')

	monkeypatch.setattr(luks, 'SysCommand', fail_modprobe)

	with pytest.raises(DiskError, match='dm-crypt kernel support is unavailable'):
		luks.ensure_dm_crypt_available()


def test_swap_mapper_is_activated(monkeypatch: pytest.MonkeyPatch) -> None:
	mapper = Path('/dev/mapper/cryptswap')
	activated: list[Path] = []
	monkeypatch.setattr(luks, 'SysCommand', lambda command: FakeCommand('swap\n'))
	monkeypatch.setattr(luks, 'swapon', lambda path: activated.append(path))

	assert luks.activate_swap_mapper_if_needed(mapper)
	assert activated == [mapper]


def test_non_swap_mapper_is_not_activated(monkeypatch: pytest.MonkeyPatch) -> None:
	mapper = Path('/dev/mapper/root')
	activated: list[Path] = []
	monkeypatch.setattr(luks, 'SysCommand', lambda command: FakeCommand('btrfs\n'))
	monkeypatch.setattr(luks, 'swapon', lambda path: activated.append(path))

	assert not luks.activate_swap_mapper_if_needed(mapper)
	assert activated == []
