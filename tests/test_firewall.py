import asyncio

from pytest import MonkeyPatch

from archinstall.lib.applications.application_menu import select_firewall
from archinstall.lib.menu.helpers import Selection
from archinstall.lib.models.application import Firewall, FirewallConfiguration
from archinstall.tui.result import Result


def test_firewalld_is_the_interactive_default(monkeypatch: MonkeyPatch) -> None:
	async def select_focused(selection: Selection[Firewall]) -> Result[Firewall]:
		assert selection._group.default_item is not None
		assert selection._group.default_item.value == Firewall.FWD
		assert selection._group.focus_item is not None
		return Result.selection(selection._group.focus_item.value)

	monkeypatch.setattr(Selection, 'show', select_focused)

	assert asyncio.run(select_firewall()) == FirewallConfiguration(Firewall.FWD)
