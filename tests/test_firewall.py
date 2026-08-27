import asyncio

from pytest import MonkeyPatch

from archinstall.lib.applications.application_menu import select_firewall
from archinstall.lib.menu.helpers import Selection
from archinstall.lib.models.application import Firewall, FirewallConfiguration
from archinstall.tui.result import Result


def test_firewall_menu_marks_recommended_and_focuses_first(monkeypatch: MonkeyPatch) -> None:
	async def select_focused(selection: Selection[Firewall]) -> Result[Firewall]:
		group = selection._group
		# The recommended option stays labelled with "(default)"...
		assert group.default_item is not None
		assert group.default_item.value == Firewall.FWD
		# ...but the cursor starts on the first option, consistent with every
		# other choice prompt.
		first = group.get_enabled_items()[0]
		assert group.focus_item is first
		return Result.selection(first.value)

	monkeypatch.setattr(Selection, 'show', select_focused)

	first_firewall = next(iter(Firewall))
	assert asyncio.run(select_firewall()) == FirewallConfiguration(first_firewall)
