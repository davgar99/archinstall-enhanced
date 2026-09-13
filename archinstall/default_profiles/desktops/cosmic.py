from typing import override

from archinstall.default_profiles.desktops.utils import (
	DesktopFlavorOption,
	DesktopInstallFlavor,
	desktop_flavor_of,
	select_desktop_flavor,
)
from archinstall.default_profiles.profile import CustomSetting, DisplayServerType, GreeterType, Profile, ProfileType
from archinstall.lib.translationhandler import tr


def _cosmic_flavor_options() -> tuple[DesktopFlavorOption, ...]:
	return (
		DesktopFlavorOption(
			DesktopInstallFlavor.Basic,
			tr('Core COSMIC session and required desktop components with the smallest package set.'),
			('cosmic-session', 'xdg-user-dirs'),
		),
		DesktopFlavorOption(
			DesktopInstallFlavor.Standard,
			tr('The complete Arch Linux cosmic package group for the normal COSMIC desktop experience.'),
			('cosmic', 'xdg-user-dirs'),
		),
		DesktopFlavorOption(
			DesktopInstallFlavor.Complete,
			tr('Standard COSMIC plus keyring, printer settings, and GTK settings integration.'),
			('cosmic', 'xdg-user-dirs', 'gnome-keyring', 'system-config-printer', 'dconf'),
		),
	)


class CosmicProfile(Profile):
	def __init__(self) -> None:
		super().__init__(
			'Cosmic',
			ProfileType.DesktopEnv,
			support_gfx_driver=True,
			display_server=DisplayServerType.Wayland,
		)

	@property
	@override
	def packages(self) -> list[str]:
		if flavor := desktop_flavor_of(self):
			options = {option.flavor: option for option in _cosmic_flavor_options()}
			return list(options[flavor].packages)

		# Preserve the historical package set for saved configurations that
		# predate desktop flavor selection.
		return [
			'cosmic',
			'xdg-user-dirs',
		]

	@property
	@override
	def default_greeter_type(self) -> GreeterType:
		return GreeterType.CosmicSession

	@override
	async def do_on_select(self) -> None:
		preset = desktop_flavor_of(self) or DesktopInstallFlavor.Standard
		flavor = await select_desktop_flavor('Cosmic', _cosmic_flavor_options(), preset)
		self.custom_settings[CustomSetting.DesktopFlavor] = flavor.value
