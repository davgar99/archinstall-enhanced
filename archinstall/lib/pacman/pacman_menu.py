from typing import assert_never, override

from archinstall.lib.menu.abstract_menu import AbstractSubMenu
from archinstall.lib.menu.helpers import Confirmation, Input
from archinstall.lib.models.pacman import PacmanConfiguration
from archinstall.lib.pathnames import PACMAN_CONF
from archinstall.lib.translationhandler import tr
from archinstall.tui.menu_item import MenuItem, MenuItemGroup
from archinstall.tui.result import ResultType


class PacmanMenu(AbstractSubMenu[PacmanConfiguration]):
	def __init__(
		self,
		pacman_conf: PacmanConfiguration,
	):
		self._pacman_conf = pacman_conf
		menu_options = self._define_menu_options()

		self._item_group = MenuItemGroup(menu_options, sort_items=False, checkmarks=True)
		super().__init__(
			self._item_group,
			config=self._pacman_conf,
			allow_reset=True,
		)

	def _define_menu_options(self) -> list[MenuItem]:
		return [
			MenuItem(
				text=tr('Parallel downloads'),
				action=select_parallel_downloads,
				value=self._pacman_conf.parallel_downloads,
				preview_action=lambda item: f'{tr("Parallel downloads")}: {item.get_value()}',
				key='parallel_downloads',
			),
			MenuItem(
				text=tr('Color'),
				action=select_color,
				value=self._pacman_conf.color,
				preview_action=lambda item: f'{tr("Color")}: {tr("Enabled") if item.get_value() else tr("Disabled")}',
				key='color',
			),
			MenuItem(
				text=tr('ILoveCandy'),
				action=select_ilove_candy,
				value=self._pacman_conf.ilove_candy,
				preview_action=lambda item: f'{tr("ILoveCandy")}: {tr("Enabled") if item.get_value() else tr("Disabled")}',
				key='ilove_candy',
			),
		]

	@override
	async def show(self) -> PacmanConfiguration | None:
		config = await super().show()

		if config is None:
			return PacmanConfiguration()

		_apply_to_live(config)

		return config


def _apply_to_live(config: PacmanConfiguration) -> None:
	"""Apply selected Pacman settings to the live system."""
	from archinstall.lib.pacman.config import configure_pacman_options

	configure_pacman_options(PACMAN_CONF, config)


async def select_parallel_downloads(preset: int = 5) -> int | None:
	max_recommended = 10

	header = tr(
		'Parallel downloads let Pacman fetch several packages at once, which can shorten installation time. Enter the number of simultaneous downloads (1-{}).'
	).format(max_recommended)

	def validator(s: str) -> str | None:
		try:
			value = int(s)
			if 1 <= value <= max_recommended:
				return None
			return tr('Value must be between 1 and {}').format(max_recommended)
		except Exception:
			return tr('Please enter a valid number')

	result = await Input(
		header=header,
		allow_skip=True,
		allow_reset=True,
		validator_callback=validator,
		default_value=str(preset),
	).show()

	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Reset:
			return 5
		case ResultType.Selection:
			return int(result.get_value())
		case _:
			assert_never(result.type_)


async def select_color(preset: bool = True) -> bool | None:
	result = await Confirmation(
		header=tr('Enable colored Pacman output? This makes package names, versions, and status messages easier to distinguish.'),
		preset=preset,
		allow_skip=True,
	).show()

	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Reset:
			return True
		case ResultType.Selection:
			return result.get_value()
		case _:
			assert_never(result.type_)


async def select_ilove_candy(preset: bool = False) -> bool | None:
	result = await Confirmation(
		header=tr("Enable ILoveCandy? This changes Pacman's progress bar appearance only and does not affect package operations."),
		preset=preset,
		allow_skip=True,
	).show()

	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Reset:
			return False
		case ResultType.Selection:
			return result.get_value()
		case _:
			assert_never(result.type_)
