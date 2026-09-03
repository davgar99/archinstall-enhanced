from collections.abc import Callable
from typing import Any

import pytest

from archinstall.default_profiles.desktops.hyprland import HyprlandProfile
from archinstall.default_profiles.desktops.labwc import LabwcProfile
from archinstall.default_profiles.desktops.niri import NiriProfile
from archinstall.default_profiles.desktops.sway import SwayProfile
from archinstall.default_profiles.desktops.utils import SeatAccess, provision_seat_access
from archinstall.default_profiles.profile import CustomSetting, Profile
from archinstall.lib.models.users import Password, User

SEAT_PROFILES: list[Callable[[], Profile]] = [SwayProfile, HyprlandProfile, NiriProfile, LabwcProfile]


class FakeInstaller:
	def __init__(self) -> None:
		self.commands: list[str] = []

	def arch_chroot(self, cmd: str, *args: Any, **kwargs: Any) -> None:
		self.commands.append(cmd)


def _profile_with(profile_type: Callable[[], Profile], setting: str | None) -> Profile:
	profile = profile_type()
	profile.custom_settings[CustomSetting.SeatAccess] = setting
	return profile


def test_saved_and_legacy_settings_are_read_back() -> None:
	assert SeatAccess.from_setting('seatd') is SeatAccess.Seatd
	assert SeatAccess.from_setting('systemd-logind') is SeatAccess.Logind
	assert SeatAccess.from_setting('polkit') is SeatAccess.Logind
	assert SeatAccess.from_setting(None) is None


def test_unknown_setting_is_ignored() -> None:
	assert SeatAccess.from_setting('not-a-seat-manager') is None


def test_seat_access_dependencies() -> None:
	assert SeatAccess.Seatd.packages == ['seatd']
	assert SeatAccess.Seatd.services == ['seatd']
	assert SeatAccess.Logind.packages == ['polkit']
	assert SeatAccess.Logind.services == []


@pytest.mark.parametrize('profile_type', SEAT_PROFILES)
@pytest.mark.parametrize('setting', ['seatd', 'systemd-logind', 'polkit'])
def test_profiles_install_every_service_they_enable(profile_type: Callable[[], Profile], setting: str) -> None:
	profile = _profile_with(profile_type, setting)
	assert set(profile.services) <= set(profile.packages)


@pytest.mark.parametrize('profile_type', SEAT_PROFILES)
def test_profiles_have_no_seat_dependencies_before_selection(profile_type: Callable[[], Profile]) -> None:
	profile = _profile_with(profile_type, None)
	assert profile.services == []
	assert 'seatd' not in profile.packages
	assert 'polkit' not in profile.packages


def test_seatd_adds_users_to_seat_group() -> None:
	installer = FakeInstaller()
	users = [User('alice', Password(plaintext='pw'), False), User('bob', Password(plaintext='pw'), False)]

	provision_seat_access(installer, users, 'seatd')  # type: ignore[arg-type]

	assert installer.commands == ['usermod -a -G seat alice', 'usermod -a -G seat bob']


@pytest.mark.parametrize('setting', ['systemd-logind', 'polkit'])
def test_logind_does_not_change_group_membership(setting: str) -> None:
	installer = FakeInstaller()
	users = [User('alice', Password(plaintext='pw'), False)]

	provision_seat_access(installer, users, setting)  # type: ignore[arg-type]

	assert installer.commands == []
