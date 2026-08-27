"""Public facade for Archinstall's Textual menus and activity feedback."""

from typing import TYPE_CHECKING, Any

from archinstall.tui.presentation import Activity, ActivityCancelled, ActivityReporter, InstallationOutcome

if TYPE_CHECKING:
	from archinstall.lib.menu.helpers import Confirmation, Input, Notify, Selection, Table

__all__ = [
	'Activity',
	'ActivityCancelled',
	'ActivityReporter',
	'Confirmation',
	'Input',
	'InstallationOutcome',
	'Notify',
	'Selection',
	'Table',
]


def __getattr__(name: str) -> Any:
	"""Load menu wrappers lazily so screen modules can import without cycles."""
	if name in {'Selection', 'Confirmation', 'Input', 'Notify', 'Table'}:
		from archinstall.lib.menu import helpers

		return getattr(helpers, name)
	raise AttributeError(name)
