from typing import override

from archinstall.default_profiles.desktops.utils import (
	DesktopFlavorOption,
	DesktopInstallFlavor,
	desktop_flavor_of,
	select_desktop_flavor,
)
from archinstall.default_profiles.profile import CustomSetting, DisplayServerType, GreeterType, Profile, ProfileType
from archinstall.lib.translationhandler import tr


def _deepin_flavor_options() -> tuple[DesktopFlavorOption, ...]:
	return (
		DesktopFlavorOption(
			DesktopInstallFlavor.Basic,
			tr('Core Deepin desktop group with no additional application collection.'),
			('deepin',),
		),
		DesktopFlavorOption(
			DesktopInstallFlavor.Standard,
			tr('Core Deepin desktop plus the terminal and editor used by the historical installer profile.'),
			('deepin', 'deepin-terminal', 'deepin-editor'),
		),
		DesktopFlavorOption(
			DesktopInstallFlavor.Complete,
			tr('Core Deepin desktop plus the deepin-extra group of additional desktop applications.'),
			('deepin', 'deepin-extra'),
		),
	)


class DeepinProfile(Profile):
	def __init__(self) -> None:
		super().__init__(
			'Deepin',
			ProfileType.DesktopEnv,
			support_gfx_driver=True,
			display_server=DisplayServerType.Xorg,
		)

	@property
	@override
	def packages(self) -> list[str]:
		if flavor := desktop_flavor_of(self):
			options = {option.flavor: option for option in _deepin_flavor_options()}
			return list(options[flavor].packages)

		# Preserve the historical package set for saved configurations that
		# predate desktop flavor selection.
		return [
			'deepin',
			'deepin-terminal',
			'deepin-editor',
		]

	@property
	@override
	def default_greeter_type(self) -> GreeterType:
		return GreeterType.Lightdm

	@override
	async def do_on_select(self) -> None:
		preset = desktop_flavor_of(self) or DesktopInstallFlavor.Standard
		flavor = await select_desktop_flavor('Deepin', _deepin_flavor_options(), preset)
		self.custom_settings[CustomSetting.DesktopFlavor] = flavor.value
