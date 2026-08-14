from typing import override

from archinstall.lib.menu.abstract_menu import AbstractSubMenu
from archinstall.lib.menu.helpers import Selection
from archinstall.lib.models.gaming import (
	CPUScheduler,
	CPUSchedulerConfiguration,
	CPUSchedulerStability,
	GamingConfiguration,
)
from archinstall.lib.translationhandler import tr
from archinstall.tui.menu_item import MenuItem, MenuItemGroup
from archinstall.tui.result import ResultType


class GamingMenu(AbstractSubMenu[GamingConfiguration]):
	def __init__(self, preset: GamingConfiguration | None = None) -> None:
		self._gaming_config = preset if preset else GamingConfiguration()
		menu_options = [
			MenuItem(
				text=tr('CPU scheduler'),
				action=select_cpu_scheduler,
				preview_action=self._prev_cpu_scheduler,
				key='cpu_scheduler_config',
			),
		]
		self._item_group = MenuItemGroup(menu_options, checkmarks=True)

		super().__init__(
			self._item_group,
			config=self._gaming_config,
			allow_reset=True,
		)

	@override
	async def show(self) -> GamingConfiguration | None:
		return await super().show()

	def _prev_cpu_scheduler(self, item: MenuItem) -> str | None:
		if item.value is not None:
			config: CPUSchedulerConfiguration = item.value
			return config.scheduler.value
		return None


def _scheduler_menu_items() -> list[MenuItem]:
	items: list[MenuItem] = []

	for stability in CPUSchedulerStability:
		items.append(MenuItem(text=stability.display_name(), read_only=True))
		schedulers = sorted(
			(scheduler for scheduler in CPUScheduler if scheduler.stability() == stability),
			key=lambda scheduler: scheduler.value,
		)

		for scheduler in schedulers:
			if scheduler.supported_by_scx_loader():
				items.append(MenuItem(text=f'  {scheduler.value}', value=scheduler))
			else:
				items.append(
					MenuItem(
						text=f'  {scheduler.value} ({tr("not supported by scx_loader")})',
						read_only=True,
					)
				)

	return items


async def select_cpu_scheduler(preset: CPUSchedulerConfiguration | None = None) -> CPUSchedulerConfiguration | None:
	group = MenuItemGroup(_scheduler_menu_items(), sort_items=False)

	if preset:
		group.set_focus_by_value(preset.scheduler)

	header = tr(
		'Select one sched-ext CPU scheduler. Experimental schedulers may be unstable. '
		'Schedulers not supported by scx_loader are shown but cannot be selected.'
	)
	result = await Selection[CPUScheduler](
		group,
		header=header,
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
