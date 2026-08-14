from typing import override

from archinstall.lib.menu.abstract_menu import AbstractSubMenu
from archinstall.lib.menu.helpers import Confirmation, Selection
from archinstall.lib.models.gaming import (
	CPUScheduler,
	CPUSchedulerConfiguration,
	CPUSchedulerStability,
	GamingConfiguration,
	NTSyncConfiguration,
)
from archinstall.lib.translationhandler import tr
from archinstall.tui.menu_item import MenuItem, MenuItemGroup
from archinstall.tui.result import ResultType


class GamingMenu(AbstractSubMenu[GamingConfiguration]):
	def __init__(self, preset: GamingConfiguration | None = None) -> None:
		self._gaming_config = preset if preset else GamingConfiguration()
		self._item_group = MenuItemGroup(
			[
				MenuItem(
					text=tr('CPU scheduler'),
					action=select_cpu_scheduler,
					preview_action=self._prev_cpu_scheduler,
					key='cpu_scheduler_config',
				),
				MenuItem(
					text=tr('NTSYNC'),
					action=select_ntsync,
					preview_action=self._prev_ntsync,
					key='ntsync_config',
				),
			],
			checkmarks=True,
		)

		super().__init__(
			self._item_group,
			config=self._gaming_config,
			allow_reset=True,
		)

	@override
	async def show(self) -> GamingConfiguration | None:
		return await super().show()

	def _prev_cpu_scheduler(self, item: MenuItem) -> str | None:
		if item.value is None:
			return None

		config: CPUSchedulerConfiguration = item.value
		return config.scheduler.value

	def _prev_ntsync(self, item: MenuItem) -> str | None:
		if item.value is None:
			return None

		config: NTSyncConfiguration = item.value
		status = tr('Enabled') if config.enabled else tr('Disabled')
		return f'{tr("NTSYNC")}: {status}'


def _scheduler_menu_items() -> list[MenuItem]:
	items: list[MenuItem] = []

	for stability in CPUSchedulerStability:
		items.append(MenuItem(text=stability.display_name(), read_only=True))
		schedulers = sorted(
			(scheduler for scheduler in CPUScheduler if scheduler.stability() == stability),
			key=lambda scheduler: scheduler.value,
		)
		items.extend(MenuItem(text=f'  {scheduler.value}', value=scheduler) for scheduler in schedulers)

	return items


async def select_cpu_scheduler(preset: CPUSchedulerConfiguration | None = None) -> CPUSchedulerConfiguration | None:
	group = MenuItemGroup(_scheduler_menu_items(), sort_items=False)

	if preset:
		group.set_focus_by_value(preset.scheduler)

	result = await Selection[CPUScheduler](
		group,
		header=tr('Select one sched-ext CPU scheduler. Experimental schedulers may be unstable.'),
		allow_skip=True,
		allow_reset=True,
		multi=False,
	).show()

	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Selection:
			return CPUSchedulerConfiguration(scheduler=result.get_value())
		case ResultType.Reset:
			return None

	raise ValueError('Unhandled result type')


async def select_ntsync(preset: NTSyncConfiguration | None = None) -> NTSyncConfiguration | None:
	result = await Confirmation(
		header=tr(
			'Enable NTSYNC? This installs ntsync-autoload so the ntsync kernel module is loaded automatically at boot.'
		),
		allow_skip=True,
		preset=preset.enabled if preset else False,
	).show()

	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Selection:
			return NTSyncConfiguration(enabled=result.get_value())
		case _:
			raise ValueError('Unhandled result type')
