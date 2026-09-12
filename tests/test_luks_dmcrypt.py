from pathlib import Path

import pytest

from archinstall.lib.disk import luks
from archinstall.lib.exceptions import DiskError, SysCallError


class FakeCommand:
	def __init__(self, output: str) -> None:
		self.output = output

	def decode(self) -> str:
		return self.output


class FakeEraseWorker:
	def __init__(self, command: str, exit_code: int = 0) -> None:
		self.command = command
		self.exit_code = exit_code
		self.poll_calls = 0
		self.write_calls: list[tuple[bytes, bool]] = []
		self.alive_checks = 0

	def poll(self) -> None:
		self.poll_calls += 1

	def write(self, data: bytes, line_ending: bool = True) -> int:
		self.write_calls.append((data, line_ending))
		return len(data)

	def is_alive(self) -> bool:
		self.alive_checks += 1
		return self.alive_checks == 1

	def decode(self) -> str:
		return 'erase failed'


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

	def sys_command(_command: str) -> FakeCommand:
		return FakeCommand('swap\n')

	monkeypatch.setattr(luks, 'SysCommand', sys_command)
	monkeypatch.setattr(luks, 'swapon', activated.append)

	assert luks.activate_swap_mapper_if_needed(mapper)
	assert activated == [mapper]


def test_non_swap_mapper_is_not_activated(monkeypatch: pytest.MonkeyPatch) -> None:
	mapper = Path('/dev/mapper/root')
	activated: list[Path] = []

	def sys_command(_command: str) -> FakeCommand:
		return FakeCommand('btrfs\n')

	monkeypatch.setattr(luks, 'SysCommand', sys_command)
	monkeypatch.setattr(luks, 'swapon', activated.append)

	assert not luks.activate_swap_mapper_if_needed(mapper)
	assert activated == []


def test_luks_erase_waits_for_worker_completion(monkeypatch: pytest.MonkeyPatch) -> None:
	worker = FakeEraseWorker('')
	monkeypatch.setattr(luks, 'SysCommandWorker', lambda command: worker)

	luks.Luks2(Path('/dev/test')).erase()

	assert worker.write_calls == [(b'YES\n', False)]
	assert worker.alive_checks >= 2


def test_luks_erase_surfaces_command_failure(monkeypatch: pytest.MonkeyPatch) -> None:
	worker = FakeEraseWorker('', exit_code=2)
	monkeypatch.setattr(luks, 'SysCommandWorker', lambda command: worker)

	with pytest.raises(DiskError, match='Could not erase LUKS metadata'):
		luks.Luks2(Path('/dev/test')).erase()
