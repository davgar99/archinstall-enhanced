from typing import override

from archinstall.default_profiles.desktops.utils import (
	DesktopFlavorOption,
	DesktopInstallFlavor,
	desktop_flavor_of,
	select_desktop_flavor,
)
from archinstall.default_profiles.profile import CustomSetting, DisplayServerType, GreeterType, Profile, ProfileType
from archinstall.lib.translationhandler import tr


def _mate_flavor_options() -> tuple[DesktopFlavorOption, ...]:
	return (
		DesktopFlavorOption(
			DesktopInstallFlavor.Basic,
			tr('Core MATE desktop group with no additional application collection.'),
			('mate',),
		),
		DesktopFlavorOption(
			DesktopInstallFlavor.Standard,
			tr('Core MATE desktop plus a terminal, archive manager, and document viewer for a practical default desktop.'),
			('mate', 'mate-terminal', 'engrampa', 'atril'),
		),
		DesktopFlavorOption(
			DesktopInstallFlavor.Complete,
			tr('Full MATE desktop plus the mate-extra group of integrated applications and Caja extensions.'),
			('mate', 'mate-extra'),
		),
	)


class MateProfile(Profile):
	def __init__(self) -> None:
		super().__init__(
			'Mate',
			ProfileType.DesktopEnv,
			support_gfx_driver=True,
			display_server=DisplayServerType.Xorg,
		)

	@property
	@override
	def packages(self) -> list[str]:
		if flavor := desktop_flavor_of(self):
			options = {option.flavor: option for option in _mate_flavor_options()}
			return list(options[flavor].packages)

		# Preserve the historical package set for saved configurations that
		# predate desktop flavor selection.
		return [
			'mate',
			'mate-extra',
		]

	@property
	@override
	def default_greeter_type(self) -> GreeterType:
		return GreeterType.Lightdm

	@override
	async def do_on_select(self) -> None:
		preset = desktop_flavor_of(self) or DesktopInstallFlavor.Standard
		flavor = await select_desktop_flavor('Mate', _mate_flavor_options(), preset)
		self.custom_settings[CustomSetting.DesktopFlavor] = flavor.value
