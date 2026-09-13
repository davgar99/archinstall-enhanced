from enum import StrEnum
from typing import override

from archinstall.default_profiles.desktops.utils import (
	DesktopFlavorOption,
	DesktopInstallFlavor,
	desktop_flavor_of,
	select_desktop_flavor,
)
from archinstall.default_profiles.profile import CustomSetting, DisplayServerType, GreeterType, Profile, ProfileType
from archinstall.lib.translationhandler import tr


class GnomeFlavor(StrEnum):
	Full = 'gnome'
	Minimal = 'gnome-minimal'

	def show(self) -> str:
		match self:
			case GnomeFlavor.Full:
				return f'gnome ({tr("Full")})'
			case GnomeFlavor.Minimal:
				return f'gnome-minimal ({tr("Recommended")})'

	def description(self) -> str:
		match self:
			case GnomeFlavor.Full:
				return tr('Installs the full gnome package group.\nIncludes all GNOME apps such as Maps, Contacts,\nCharacters, Calendar, Weather, and more.')
			case GnomeFlavor.Minimal:
				return tr(
					'Installs a minimal GNOME environment.\n'
					'Includes only the essential components:\n'
					'  - gnome-shell\n'
					'  - gnome-session\n'
					'  - gnome-terminal\n'
					'  - gnome-control-center\n'
					'  - gnome-settings-daemon\n'
					'  - nautilus\n'
					'  - xdg-desktop-portal-gnome\n'
					'  - gnome-tweaks'
				)

	def packages(self) -> list[str]:
		match self:
			case GnomeFlavor.Full:
				return [
					'gnome',
					'gnome-tweaks',
				]
			case GnomeFlavor.Minimal:
				return [
					'gnome-shell',
					'gnome-session',
					'gnome-terminal',
					'gnome-control-center',
					'gnome-settings-daemon',
					'nautilus',
					'xdg-desktop-portal-gnome',
					'gnome-tweaks',
				]


def _gnome_flavor_options() -> tuple[DesktopFlavorOption, ...]:
	return (
		DesktopFlavorOption(
			DesktopInstallFlavor.Basic,
			tr('Core GNOME shell, settings, file manager, terminal, portal, and tweak tools without the full application collection.'),
			tuple(GnomeFlavor.Minimal.packages()),
		),
		DesktopFlavorOption(
			DesktopInstallFlavor.Standard,
			tr('Balanced GNOME desktop using the Arch Linux gnome group plus GNOME Tweaks.'),
			('gnome', 'gnome-tweaks'),
		),
		DesktopFlavorOption(
			DesktopInstallFlavor.Complete,
			tr('Broad GNOME installation with the standard desktop plus the additional gnome-extra application group.'),
			('gnome', 'gnome-extra', 'gnome-tweaks'),
		),
	)


class GnomeProfile(Profile):
	def __init__(self) -> None:
		super().__init__(
			'GNOME',
			ProfileType.DesktopEnv,
			support_gfx_driver=True,
			display_server=DisplayServerType.Wayland,
		)

	def _selected_flavor(self) -> GnomeFlavor:
		flavor = self.custom_settings.get(CustomSetting.GnomeFlavor)
		if flavor is None:
			return GnomeFlavor.Minimal
		try:
			return GnomeFlavor(flavor)
		except (TypeError, ValueError):  # fmt: skip
			# Persisted configurations can outlive flavor names. Fall back to the
			# historical default instead of aborting profile loading.
			return GnomeFlavor.Minimal

	def _menu_flavor(self) -> DesktopInstallFlavor:
		if flavor := desktop_flavor_of(self):
			return flavor

		legacy = self.custom_settings.get(CustomSetting.GnomeFlavor)
		if legacy == GnomeFlavor.Minimal.value:
			return DesktopInstallFlavor.Basic
		return DesktopInstallFlavor.Standard

	@property
	@override
	def packages(self) -> list[str]:
		if flavor := desktop_flavor_of(self):
			options = {option.flavor: option for option in _gnome_flavor_options()}
			return list(options[flavor].packages)
		return self._selected_flavor().packages()

	@property
	@override
	def default_greeter_type(self) -> GreeterType:
		return GreeterType.Gdm

	async def _select_flavor(self) -> None:
		flavor = await select_desktop_flavor('GNOME', _gnome_flavor_options(), self._menu_flavor())
		self.custom_settings[CustomSetting.DesktopFlavor] = flavor.value

	@override
	async def do_on_select(self) -> None:
		await self._select_flavor()
