from typing import assert_never, override

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
	def __init__(self, preset: GamingConfiguration | None = None, advanced: bool = False) -> None:
		self._gaming_config = preset if preset else GamingConfiguration()
		self._item_group = MenuItemGroup(
			[
				MenuItem(text=tr('Graphics'), read_only=True),
				MenuItem(
					text=tr('Install 32-bit graphics libraries'),
					action=select_32bit_graphics,
					preview_action=self._prev_toggle,
					key='install_32bit_graphics',
				),
				MenuItem(text=tr('Compatibility'), read_only=True),
				MenuItem(
					text=tr('NTSYNC'),
					action=select_ntsync,
					preview_action=self._prev_ntsync,
					key='ntsync_config',
				),
				MenuItem(
					text=tr('Increase vm.max_map_count'),
					action=select_vm_max_map_count,
					preview_action=self._prev_toggle,
					key='increase_vm_max_map_count',
				),
				MenuItem(
					text=tr('Increase shader cache size'),
					action=select_shader_cache,
					preview_action=self._prev_toggle,
					key='increase_shader_cache',
				),
				MenuItem(text=tr('Performance'), read_only=True),
				MenuItem(
					text=tr('CPU scheduler'),
					action=select_cpu_scheduler,
					preview_action=self._prev_cpu_scheduler,
					key='cpu_scheduler_config',
				),
				MenuItem(
					text=tr('GameMode'),
					action=select_gamemode,
					preview_action=self._prev_toggle,
					key='gamemode',
				),
				MenuItem(text=tr('Tools'), read_only=True),
				MenuItem(
					text=tr('MangoHud'),
					action=select_mangohud,
					preview_action=self._prev_toggle,
					key='mangohud',
				),
				MenuItem(
					text=tr('Gamescope'),
					action=select_gamescope,
					preview_action=self._prev_toggle,
					key='gamescope',
				),
				MenuItem(text=tr('Controllers'), read_only=True),
				MenuItem(
					text=tr('Disable PlayStation controller touchpads as a mouse'),
					action=select_playstation_touchpad,
					preview_action=self._prev_toggle,
					key='disable_playstation_touchpad',
				),
				MenuItem(text=tr('Advanced'), read_only=True, enabled=advanced),
				MenuItem(
					text=tr('Disable hardware watchdog'),
					action=select_disable_watchdog,
					preview_action=self._prev_toggle,
					key='disable_watchdog',
					enabled=advanced,
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
		return f'{tr("CPU scheduler")}: {config.scheduler.value}'

	def _prev_ntsync(self, item: MenuItem) -> str | None:
		if item.value is None:
			return None

		config: NTSyncConfiguration = item.value
		status = tr('Enabled') if config.enabled else tr('Disabled')
		return f'{tr("NTSYNC")}: {status}'

	def _prev_toggle(self, item: MenuItem) -> str | None:
		if item.value is None:
			return None

		status = tr('Enabled') if item.value else tr('Disabled')
		return f'{item.text}: {status}'


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
		header=tr(
			'Select a sched-ext CPU scheduler. It controls how CPU time is distributed between applications.\n'
			'Gaming mode favors responsiveness; experimental schedulers may be unstable.'
		),
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
		case _:
			assert_never(result.type_)


async def select_ntsync(preset: NTSyncConfiguration | None = None) -> NTSyncConfiguration | None:
	result = await Confirmation(
		header=tr(
			'Enable NTSYNC autoload? NTSYNC provides efficient Windows-compatible synchronization for Wine and Proton. '
			'Official Arch kernels support it, and current Wine and Proton versions use it automatically when available.'
		),
		allow_skip=True,
		preset=preset.enabled if preset else True,
	).show()

	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Selection:
			return NTSyncConfiguration(enabled=result.get_value())
		case ResultType.Reset:
			raise ValueError('Unhandled result type')
		case _:
			assert_never(result.type_)


async def _select_toggle(header: str, preset: bool | None) -> bool | None:
	result = await Confirmation(
		header=header,
		allow_skip=True,
		preset=preset if preset is not None else False,
	).show()

	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Selection:
			return result.get_value()
		case ResultType.Reset:
			raise ValueError('Unhandled result type')
		case _:
			assert_never(result.type_)


async def select_vm_max_map_count(preset: bool | None = None) -> bool | None:
	return await _select_toggle(
		tr(
			'Increase vm.max_map_count to the SteamOS value (2147483642) for memory-map-heavy games? '
			'This can improve Wine and Proton compatibility, but current Arch defaults are sufficient for most games. '
			'ArchWiki warns that the higher value can break older programs that read core dump files.'
		),
		preset,
	)


async def select_shader_cache(preset: bool | None = None) -> bool | None:
	return await _select_toggle(
		tr(
			'Increase the shader cache limit to 12 GB? A larger cache can reduce shader recompilation and repeat stuttering, '
			'but it may use more disk space. This applies the CachyOS-recommended limits for Mesa and Nvidia drivers.'
		),
		preset,
	)


async def select_32bit_graphics(preset: bool | None = None) -> bool | None:
	return await _select_toggle(
		tr(
			'Install 32-bit OpenGL and Vulkan drivers for the selected GPU? Steam, Wine, Proton, and older games may require them. '
			'This enables the Multilib repository and uses additional disk space.'
		),
		True if preset is None else preset,
	)


async def select_playstation_touchpad(preset: bool | None = None) -> bool | None:
	return await _select_toggle(
		tr(
			'Disable DualShock 4 and DualSense touchpads as desktop mouse devices? Games can still access the controllers directly, '
			'but the touchpads will no longer move the desktop pointer through libinput.'
		),
		preset,
	)


async def select_gamemode(preset: bool | None = None) -> bool | None:
	return await _select_toggle(
		tr('Enable GameMode? Games can request temporary CPU, process-priority, and power-management optimizations.'),
		preset,
	)


async def select_mangohud(preset: bool | None = None) -> bool | None:
	return await _select_toggle(
		tr('Enable MangoHud? It displays FPS, frame times, temperatures, and other performance information in games.'),
		preset,
	)


async def select_gamescope(preset: bool | None = None) -> bool | None:
	return await _select_toggle(
		tr("Enable Gamescope? Valve's gaming compositor can isolate games, control resolution and scaling, and limit frame rates."),
		preset,
	)


async def select_disable_watchdog(preset: bool | None = None) -> bool | None:
	return await _select_toggle(
		tr(
			'Disable the hardware watchdog? This may prevent watchdog-related freezes or unwanted resets on affected hardware, '
			'but the system will lose automatic recovery from some hardware lockups.'
		),
		preset,
	)
