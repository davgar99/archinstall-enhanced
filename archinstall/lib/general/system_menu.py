from typing import assert_never

from archinstall.lib.hardware import GfxDriver, SysInfo
from archinstall.lib.menu.helpers import Confirmation, Selection
from archinstall.lib.models.application import ZramAlgorithm, ZramConfiguration
from archinstall.lib.models.package_types import DEFAULT_KERNEL, Kernel
from archinstall.lib.translationhandler import tr
from archinstall.tui.menu_item import MenuItem, MenuItemGroup
from archinstall.tui.result import ResultType


def recommended_gfx_driver() -> GfxDriver:
	"""Choose the narrowest safe default for detected graphics hardware."""
	if SysInfo.virtualization() == 'oracle':
		return GfxDriver.VMOpenSource

	detected = [
		(SysInfo.has_amd_graphics(), GfxDriver.AmdOpenSource),
		(SysInfo.has_intel_graphics(), GfxDriver.IntelOpenSource),
		(SysInfo.has_nvidia_graphics(), GfxDriver.NvidiaOpenKernel),
	]
	matches = [driver for present, driver in detected if present]

	if len(matches) == 1:
		return matches[0]
	return GfxDriver.AllOpenSource


async def select_kernel(preset: list[str] | None = None) -> list[str]:
	"""
	Asks the user to select a kernel for system.

	:return: The string as a selected kernel
	:rtype: string
	"""
	if preset is None:
		preset = []

	enum_preset = [Kernel(kernel) for kernel in preset]
	group = MenuItemGroup.from_enum(Kernel, sort_items=True, preset=enum_preset)
	group.set_default_by_value(DEFAULT_KERNEL)

	result = await Selection[Kernel](
		group,
		header=tr('Select which kernel(s) to install'),
		allow_skip=True,
		allow_reset=True,
		multi=True,
	).show()

	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Reset:
			return []
		case ResultType.Selection:
			return [kernel.value for kernel in result.get_values()]


async def select_uki(preset: bool = True) -> bool:
	prompt = tr('Would you like to use unified kernel images?') + '\n'

	result = await Confirmation(header=prompt, allow_skip=True).show()

	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Selection:
			return result.get_value()
		case ResultType.Reset:
			raise ValueError('Unhandled result type')


async def select_driver(
	options: list[GfxDriver] | None = None,
	preset: GfxDriver | None = None,
) -> GfxDriver | None:
	"""
	Somewhat convoluted function, whose job is simple.
	Select a graphics driver from a pre-defined set of popular options.

	(The template xorg is for beginner users, not advanced, and should
	there for appeal to the general public first and edge cases later)
	"""
	if not options:
		options = list(GfxDriver)

	items = [
		MenuItem(
			o.value,
			value=o,
			preview_action=lambda x: x.value.packages_text() if x.value else None,
		)
		for o in options
	]

	group = MenuItemGroup(items, sort_items=True)
	recommended = recommended_gfx_driver()
	if recommended not in options:
		recommended = GfxDriver.AllOpenSource if GfxDriver.AllOpenSource in options else options[0]
	group.set_default_by_value(preset or recommended)

	header = tr('Hardware detection selected a recommended graphics driver. You can override it below.') + '\n'
	if SysInfo.has_amd_graphics():
		header += tr('AMD graphics detected.') + '\n'
	if SysInfo.has_intel_graphics():
		header += tr('Intel graphics detected.') + '\n'
	if SysInfo.has_nvidia_graphics():
		header += tr('Nvidia graphics detected.') + '\n'

	result = await Selection[GfxDriver](
		group,
		header=header,
		allow_skip=True,
		allow_reset=True,
		preview_location='right',
	).show()

	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Reset:
			return None
		case ResultType.Selection:
			return result.get_value()


async def select_swap(preset: ZramConfiguration = ZramConfiguration(enabled=True)) -> ZramConfiguration:
	prompt = tr('Enable swap on zram?') + '\n'

	result = await Confirmation(
		header=prompt,
		allow_skip=True,
	).show()

	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Selection:
			enabled = result.item() == MenuItem.yes()
			if not enabled:
				return ZramConfiguration(enabled=False)

			# Ask for compression algorithm
			algo_group = MenuItemGroup.from_enum(ZramAlgorithm, sort_items=False)
			algo_group.set_default_by_value(ZramAlgorithm.ZSTD)

			algo_result = await Selection[ZramAlgorithm](
				algo_group,
				header=tr('Select a zram compression algorithm.') + '\n',
				allow_skip=True,
			).show()

			match algo_result.type_:
				case ResultType.Skip:
					algo = preset.algorithm
				case ResultType.Selection:
					algo = algo_result.get_value()
				case ResultType.Reset:
					raise ValueError('Unhandled result type')
				case _:
					assert_never(algo_result.type_)

			return ZramConfiguration(
				enabled=True,
				algorithm=algo,
			)
		case ResultType.Reset:
			raise ValueError('Unhandled result type')
		case _:
			assert_never(result.type_)
