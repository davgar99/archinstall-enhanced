from typing import override

from archinstall.default_profiles.desktops.utils import (
	DesktopFlavorOption,
	DesktopInstallFlavor,
	desktop_flavor_of,
	select_desktop_flavor,
)
from archinstall.default_profiles.profile import CustomSetting, DisplayServerType, GreeterType, Profile, ProfileType
from archinstall.lib.translationhandler import tr


def _xfce_flavor_options() -> tuple[DesktopFlavorOption, ...]:
	return (
		DesktopFlavorOption(
			DesktopInstallFlavor.Basic,
			tr('Core Xfce desktop group with the smallest supported package set.'),
			('xfce4',),
		),
		DesktopFlavorOption(
			DesktopInstallFlavor.Standard,
			tr('Core Xfce desktop plus volume control, virtual filesystem integration, and archive support.'),
			('xfce4', 'pavucontrol', 'gvfs', 'xarchiver'),
		),
		DesktopFlavorOption(
			DesktopInstallFlavor.Complete,
			tr('Standard Xfce desktop plus the xfce4-goodies collection of plugins and additional applications.'),
			('xfce4', 'xfce4-goodies', 'pavucontrol', 'gvfs', 'xarchiver'),
		),
	)


class Xfce4Profile(Profile):
	def __init__(self) -> None:
		super().__init__(
			'Xfce4',
			ProfileType.DesktopEnv,
			support_gfx_driver=True,
			display_server=DisplayServerType.Xorg,
		)

	@property
	@override
	def packages(self) -> list[str]:
		if flavor := desktop_flavor_of(self):
			options = {option.flavor: option for option in _xfce_flavor_options()}
			return list(options[flavor].packages)

		# Preserve the historical package set for saved configurations that
		# predate desktop flavor selection.
		return [
			'xfce4',
			'xfce4-goodies',
			'pavucontrol',
			'gvfs',
			'xarchiver',
		]

	@property
	@override
	def default_greeter_type(self) -> GreeterType:
		return GreeterType.Lightdm

	@override
	async def do_on_select(self) -> None:
		preset = desktop_flavor_of(self) or DesktopInstallFlavor.Standard
		flavor = await select_desktop_flavor('Xfce4', _xfce_flavor_options(), preset)
		self.custom_settings[CustomSetting.DesktopFlavor] = flavor.value
