from typing import Any

from pytest import MonkeyPatch

from archinstall.lib.exceptions import SysCallError
from archinstall.lib.locale import utils


class CommandResult:
	def __init__(self, output: str) -> None:
		self.output = output

	def decode(self) -> str:
		return self.output


def test_keyboard_layout_falls_back_when_keymap_inventory_is_unavailable(monkeypatch: MonkeyPatch) -> None:
	def command(cmd: str, *args: Any, **kwargs: Any) -> CommandResult:
		if cmd.endswith('status'):
			return CommandResult('VC Keymap: us\n')
		raise SysCallError('keymap inventory unavailable', exit_code=1)

	monkeypatch.setattr(utils, 'SysCommand', command)

	assert utils.get_kb_layout() == ''


def test_keyboard_layout_returns_verified_layout(monkeypatch: MonkeyPatch) -> None:
	def command(cmd: str, *args: Any, **kwargs: Any) -> CommandResult:
		if cmd.endswith('status'):
			return CommandResult('VC Keymap: us\n')
		return CommandResult('de\nus\n')

	monkeypatch.setattr(utils, 'SysCommand', command)

	assert utils.get_kb_layout() == 'us'
