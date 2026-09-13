from archinstall.default_profiles.desktops.cosmic import CosmicProfile
from archinstall.default_profiles.desktops.deepin import DeepinProfile
from archinstall.default_profiles.desktops.gnome import GnomeFlavor, GnomeProfile
from archinstall.default_profiles.desktops.mate import MateProfile
from archinstall.default_profiles.desktops.plasma import PlasmaFlavor, PlasmaProfile
from archinstall.default_profiles.desktops.utils import DesktopInstallFlavor
from archinstall.default_profiles.desktops.xfce4 import Xfce4Profile
from archinstall.default_profiles.profile import CustomSetting


def _set_flavor(profile: object, flavor: DesktopInstallFlavor) -> None:
	profile.custom_settings[CustomSetting.DesktopFlavor] = flavor.value  # type: ignore[attr-defined]


def test_gnome_flavors_and_legacy_default() -> None:
	profile = GnomeProfile()
	assert profile.packages == GnomeFlavor.Minimal.packages()

	_set_flavor(profile, DesktopInstallFlavor.Basic)
	assert profile.packages == GnomeFlavor.Minimal.packages()

	_set_flavor(profile, DesktopInstallFlavor.Standard)
	assert profile.packages == ['gnome', 'gnome-tweaks']

	_set_flavor(profile, DesktopInstallFlavor.Complete)
	assert profile.packages == ['gnome', 'gnome-extra', 'gnome-tweaks']


def test_plasma_flavors_and_legacy_full_group() -> None:
	profile = PlasmaProfile()
	assert profile.packages == ['plasma-meta']

	profile.custom_settings[CustomSetting.PlasmaFlavor] = PlasmaFlavor.Plasma.value
	assert profile.packages == ['plasma']

	_set_flavor(profile, DesktopInstallFlavor.Basic)
	assert profile.packages == ['plasma-desktop']

	_set_flavor(profile, DesktopInstallFlavor.Standard)
	assert profile.packages == ['plasma-meta']

	_set_flavor(profile, DesktopInstallFlavor.Complete)
	assert 'plasma-meta' in profile.packages
	assert 'kio-admin' in profile.packages
	assert 'kio-extras' in profile.packages
	assert 'kdeconnect' in profile.packages


def test_xfce_flavors_preserve_legacy_package_set() -> None:
	profile = Xfce4Profile()
	assert 'xfce4-goodies' in profile.packages

	_set_flavor(profile, DesktopInstallFlavor.Basic)
	assert profile.packages == ['xfce4']

	_set_flavor(profile, DesktopInstallFlavor.Standard)
	assert 'xfce4-goodies' not in profile.packages
	assert 'gvfs' in profile.packages

	_set_flavor(profile, DesktopInstallFlavor.Complete)
	assert 'xfce4-goodies' in profile.packages


def test_mate_flavors_preserve_legacy_package_set() -> None:
	profile = MateProfile()
	assert profile.packages == ['mate', 'mate-extra']

	_set_flavor(profile, DesktopInstallFlavor.Basic)
	assert profile.packages == ['mate']

	_set_flavor(profile, DesktopInstallFlavor.Standard)
	assert 'mate-terminal' in profile.packages
	assert 'mate-extra' not in profile.packages

	_set_flavor(profile, DesktopInstallFlavor.Complete)
	assert profile.packages == ['mate', 'mate-extra']


def test_cosmic_flavors_preserve_legacy_package_set() -> None:
	profile = CosmicProfile()
	assert profile.packages == ['cosmic', 'xdg-user-dirs']

	_set_flavor(profile, DesktopInstallFlavor.Basic)
	assert profile.packages == ['cosmic-session', 'xdg-user-dirs']

	_set_flavor(profile, DesktopInstallFlavor.Standard)
	assert profile.packages == ['cosmic', 'xdg-user-dirs']

	_set_flavor(profile, DesktopInstallFlavor.Complete)
	assert 'gnome-keyring' in profile.packages
	assert 'system-config-printer' in profile.packages


def test_deepin_flavors_preserve_legacy_package_set() -> None:
	profile = DeepinProfile()
	assert profile.packages == ['deepin', 'deepin-terminal', 'deepin-editor']

	_set_flavor(profile, DesktopInstallFlavor.Basic)
	assert profile.packages == ['deepin']

	_set_flavor(profile, DesktopInstallFlavor.Standard)
	assert profile.packages == ['deepin', 'deepin-terminal', 'deepin-editor']

	_set_flavor(profile, DesktopInstallFlavor.Complete)
	assert profile.packages == ['deepin', 'deepin-extra']
