from dataclasses import dataclass
from enum import Enum, StrEnum

from archinstall.default_profiles.profile import CustomSetting, Profile
from archinstall.lib.installer import Installer
from archinstall.lib.log import warn
from archinstall.lib.menu.helpers import Selection
from archinstall.lib.models.users import User
from archinstall.lib.translationhandler import tr
from archinstall.tui.menu_item import MenuItem, MenuItemGroup
from archinstall.tui.result import ResultType


class DesktopInstallFlavor(StrEnum):
	Basic = 'basic'
	Standard = 'standard'
	Complete = 'complete'


@dataclass(frozen=True)
class DesktopFlavorOption:
	flavor: DesktopInstallFlavor
	description: str
	packages: tuple[str, ...]

	def menu_text(self) -> str:
		if self.flavor == DesktopInstallFlavor.Standard:
			return f'{self.flavor.name} ({tr("Recommended")})'
		return self.flavor.name

	def preview_text(self) -> str:
		packages = '\n'.join(f'- {package}' for package in self.packages)
		return f'{tr("Description")}: {self.description}\n\n{tr("Top-level package selections")}: {len(self.packages)}\n{tr("Installed packages")}:\n{packages}'


def desktop_flavor_of(profile: Profile) -> DesktopInstallFlavor | None:
	value = profile.custom_settings.get(CustomSetting.DesktopFlavor)
	if value is None:
		return None

	try:
		return DesktopInstallFlavor(value)
	except (TypeError, ValueError):  # fmt: skip
		warn(f'Unknown desktop install flavor for {profile.name}, using the legacy/default package set: {value}')
		return None


async def select_desktop_flavor(
	profile_name: str,
	options: tuple[DesktopFlavorOption, ...],
	preset: DesktopInstallFlavor = DesktopInstallFlavor.Standard,
) -> DesktopInstallFlavor:
	by_flavor = {option.flavor: option for option in options}
	items = [
		MenuItem(
			option.menu_text(),
			value=option.flavor,
			preview_action=lambda item: by_flavor[item.value].preview_text() if item.value else None,
		)
		for option in options
	]
	group = MenuItemGroup(items, sort_items=False)
	group.set_default_by_value(preset)

	result = await Selection[DesktopInstallFlavor](
		group,
		header=tr('Select how much of {} to install').format(profile_name) + '\n',
		allow_skip=False,
		preview_location='right',
	).show()

	if result.type_ == ResultType.Selection:
		return result.get_value()
	else:
		raise ValueError('Unexpected result type from desktop flavor selection')


class SeatAccess(Enum):
	Seatd = 'seatd'
	Logind = 'systemd-logind'

	@classmethod
	def from_setting(cls, value: str | None) -> SeatAccess | None:
		if value == 'polkit':
			return cls.Logind
		if value is None:
			return None

		try:
			return cls(value)
		except ValueError:
			warn(f'Unknown seat access setting, ignoring it: {value}')
			return None

	@property
	def packages(self) -> list[str]:
		match self:
			case SeatAccess.Seatd:
				return ['seatd']
			case SeatAccess.Logind:
				return ['polkit']

	@property
	def services(self) -> list[str]:
		match self:
			case SeatAccess.Seatd:
				return ['seatd']
			case SeatAccess.Logind:
				return []


def seat_access_of(profile: Profile) -> SeatAccess | None:
	return SeatAccess.from_setting(profile.custom_settings.get(CustomSetting.SeatAccess))


def provision_seat_access(
	install_session: Installer,
	users: list[User],
	seat_access: str,
) -> None:
	if SeatAccess.from_setting(seat_access) is SeatAccess.Seatd:
		for user in users:
			install_session.arch_chroot(f'usermod -a -G seat {user.username}')


async def select_seat_access(profile_name: str, default: str | None) -> SeatAccess:
	header = tr('{} needs access to your seat').format(profile_name)
	header += f' ({tr("collection of hardware devices i.e. keyboard, mouse")})' + '\n'
	header += tr('Choose an option how to give {} access to your hardware').format(profile_name)

	items = [MenuItem(s.value, value=s) for s in SeatAccess]
	group = MenuItemGroup(items, sort_items=True)

	group.set_default_by_value(SeatAccess.from_setting(default))

	result = await Selection[SeatAccess](
		group,
		header=header,
		allow_skip=False,
	).show()

	if result.type_ == ResultType.Selection:
		return result.get_value()
	else:
		raise ValueError('Unexpected result type from seat access selection')
