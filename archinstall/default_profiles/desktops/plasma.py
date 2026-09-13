from enum import StrEnum
from typing import override

from archinstall.default_profiles.desktops.utils import (
	DesktopFlavorOption,
	DesktopInstallFlavor,
	desktop_flavor_of,
	select_desktop_flavor,
)
from archinstall.default_profiles.profile import CustomSetting, DisplayServerType, GreeterType, Profile, ProfileType
from archinstall.lib.packages.packages import available_package, package_group_info
from archinstall.lib.translationhandler import tr


class PlasmaFlavor(StrEnum):
	Meta = 'plasma-meta'
	Plasma = 'plasma'
	Desktop = 'plasma-desktop'

	def show(self) -> str:
		match self:
			case PlasmaFlavor.Meta:
				return f'{self.value} ({tr("Recommended")})'
			case PlasmaFlavor.Plasma | PlasmaFlavor.Desktop:
				return self.value

	def package_details(self) -> str:
		ty = ''
		details = ''
		desc = ''

		match self:
			case PlasmaFlavor.Meta:
				ty = tr('Package')
				desc = tr('Curated selection of KDE Plasma packages')
				info = available_package(self.value)

				if info is not None:
					details = tr('Dependencies') + '\n'
					details += '\n'.join(f'- {entry}' for entry in info.get_depends_on)
			case PlasmaFlavor.Plasma:
				ty = tr('Package group')
				desc = tr('Extensive KDE Plasma installation')
				group = package_group_info(self.value)

				if group is not None:
					details = tr('Packages in group') + '\n'
					details += '\n'.join(f'- {entry}' for entry in group.packages)
			case PlasmaFlavor.Desktop:
				ty = tr('Package group')
				desc = tr('Minimal KDE Plasma installation')
				info = available_package(self.value)

				if info is not None:
					details = tr('Dependencies') + '\n'
					details += '\n'.join(f'- {entry}' for entry in info.get_depends_on)

		return f'{tr("Type")}: {ty}\n{tr("Description")}: {desc}\n\n{details}'

	def packages(self) -> list[str]:
		match self:
			case PlasmaFlavor.Meta:
				return ['plasma-meta']
			case PlasmaFlavor.Plasma:
				return ['plasma']
			case PlasmaFlavor.Desktop:
				return ['plasma-desktop']


_KDE_COMPLETE_PACKAGES = (
	'plasma-meta',
	'audiocd-kio',
	'baloo-widgets',
	'dolphin-plugins',
	'ffmpegthumbs',
	'kde-inotify-survey',
	'kdeconnect',
	'kdegraphics-thumbnailers',
	'kdenetwork-filesharing',
	'khelpcenter',
	'kimageformats',
	'kio-admin',
	'kio-extras',
	'kio-fuse',
	'kio-gdrive',
	'kwalletmanager',
	'kup',
	'libappindicator',
	'libkcddb',
	'qqc2-desktop-style',
	'qrca',
	'qt6-imageformats',
	'fwupd',
	'geoclue',
	'iio-sensor-proxy',
	'noto-fonts',
	'noto-fonts-emoji',
	'orca',
	'switcheroo-control',
	'system-config-printer',
	'tesseract',
	'tesseract-data-eng',
	'unrar',
	'xsettingsd',
)


def _plasma_flavor_options() -> tuple[DesktopFlavorOption, ...]:
	return (
		DesktopFlavorOption(
			DesktopInstallFlavor.Basic,
			tr('Core Plasma desktop for users who want to choose most optional applications and integrations themselves.'),
			('plasma-desktop',),
		),
		DesktopFlavorOption(
			DesktopInstallFlavor.Standard,
			tr('Balanced KDE Plasma installation using the Arch Linux Plasma meta package.'),
			('plasma-meta',),
		),
		DesktopFlavorOption(
			DesktopInstallFlavor.Complete,
			tr('Broad Plasma desktop with KDE-recommended file, thumbnail, sharing, backup, device, and desktop integrations.'),
			_KDE_COMPLETE_PACKAGES,
		),
	)


class PlasmaProfile(Profile):
	def __init__(self) -> None:
		super().__init__(
			'KDE Plasma',
			ProfileType.DesktopEnv,
			support_gfx_driver=True,
			display_server=DisplayServerType.Wayland,
		)

	def _menu_flavor(self) -> DesktopInstallFlavor:
		if flavor := desktop_flavor_of(self):
			return flavor

		legacy = self.custom_settings.get(CustomSetting.PlasmaFlavor)
		match legacy:
			case PlasmaFlavor.Desktop.value:
				return DesktopInstallFlavor.Basic
			case PlasmaFlavor.Plasma.value:
				return DesktopInstallFlavor.Complete
			case _:
				return DesktopInstallFlavor.Standard

	@property
	@override
	def packages(self) -> list[str]:
		if flavor := desktop_flavor_of(self):
			options = {option.flavor: option for option in _plasma_flavor_options()}
			return list(options[flavor].packages)

		flavor_str = self.custom_settings.get(CustomSetting.PlasmaFlavor)
		if flavor_str is not None:
			try:
				return PlasmaFlavor(flavor_str).packages()
			except (TypeError, ValueError):  # fmt: skip
				return PlasmaFlavor.Meta.packages()

		return PlasmaFlavor.Meta.packages()

	@property
	@override
	def default_greeter_type(self) -> GreeterType:
		return GreeterType.PlasmaLoginManager

	async def _select_flavor(self) -> None:
		flavor = await select_desktop_flavor('KDE Plasma', _plasma_flavor_options(), self._menu_flavor())
		self.custom_settings[CustomSetting.DesktopFlavor] = flavor.value

	@override
	async def do_on_select(self) -> None:
		await self._select_flavor()
