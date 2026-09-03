from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from archinstall.lib.disk import utils
from archinstall.lib.exceptions import DiskError, SysCallError
from archinstall.lib.models.device import LsblkInfo

SAMPLE_PARTITION: dict[str, Any] = {
	'name': 'sda2',
	'path': '/dev/sda2',
	'pkname': 'sda',
	'log-sec': 512,
	'size': 4294967296,
	'pttype': 'gpt',
	'ptuuid': '5f1e1b8a',
	'rota': True,
	'tran': 'sata',
	'partn': 2,
	'partuuid': '0d2a1f7c',
	'parttype': '0657fd6d-a4ab-43c4-84e5-0933c84b4f4f',
	'uuid': 'e3c9b4a1',
	'fstype': 'swap',
	'fsver': '1',
	'fsavail': None,
	'fsuse%': None,
	'type': 'part',
	'mountpoint': None,
	'mountpoints': [None],
	'fsroots': [],
}

SWAPON_QUERY = ['swapon', '--show=NAME', '--noheadings', '--raw']
SWAPON_OUTPUT = '/dev/sda2\n/swapfile\n'


def _lsblk_info(**overrides: Any) -> LsblkInfo:
	return LsblkInfo.model_validate(SAMPLE_PARTITION | overrides)


def _fake_syscommand(commands: list[list[str]], swapon_output: str = SWAPON_OUTPUT) -> Callable[[list[str]], Any]:
	class _Result:
		def decode(self) -> str:
			return swapon_output

	def _run(cmd: list[str]) -> _Result:
		commands.append(cmd)
		return _Result()

	return _run


def test_active_swap_sentinel_is_not_parsed_as_a_mountpoint() -> None:
	info = _lsblk_info(mountpoint='[SWAP]', mountpoints=['[SWAP]'])
	assert info.mountpoint is None
	assert info.mountpoints == []


def test_regular_and_bracketed_mountpoints_are_preserved() -> None:
	info = _lsblk_info(fstype='ext4', mountpoint='/mnt/[backup]', mountpoints=['/mnt/[backup]'])
	assert info.mountpoint == Path('/mnt/[backup]')
	assert info.mountpoints == [Path('/mnt/[backup]')]


def test_swapoff_skips_inactive_swap(monkeypatch: pytest.MonkeyPatch) -> None:
	commands: list[list[str]] = []
	monkeypatch.setattr(utils, 'SysCommand', _fake_syscommand(commands))
	utils.swapoff(Path('/dev/sdb1'))
	assert commands == [SWAPON_QUERY]


def test_swapoff_disables_active_swap(monkeypatch: pytest.MonkeyPatch) -> None:
	commands: list[list[str]] = []
	monkeypatch.setattr(utils, 'SysCommand', _fake_syscommand(commands))
	utils.swapoff(Path('/dev/sda2'))
	assert commands == [SWAPON_QUERY, ['swapoff', '/dev/sda2']]


def test_swapoff_resolves_symlinks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
	device = tmp_path / 'sda2'
	device.touch()
	link = tmp_path / 'by-uuid'
	link.symlink_to(device)
	commands: list[list[str]] = []
	monkeypatch.setattr(utils, 'SysCommand', _fake_syscommand(commands, f'{device}\n'))

	utils.swapoff(link)

	assert commands == [SWAPON_QUERY, ['swapoff', str(link)]]


def test_swap_query_failure_is_not_silenced(monkeypatch: pytest.MonkeyPatch) -> None:
	def _run(cmd: list[str]) -> Any:
		raise SysCallError('swapon failed', exit_code=1)

	monkeypatch.setattr(utils, 'SysCommand', _run)
	with pytest.raises(DiskError):
		utils.swapoff(Path('/dev/sda2'))


def test_swapoff_failure_is_not_silenced(monkeypatch: pytest.MonkeyPatch) -> None:
	def _run(cmd: list[str]) -> Any:
		if cmd[0] == 'swapoff':
			raise SysCallError('swapoff failed', exit_code=1)
		return _fake_syscommand([])(cmd)

	monkeypatch.setattr(utils, 'SysCommand', _run)
	with pytest.raises(DiskError):
		utils.swapoff(Path('/dev/sda2'))
