from archinstall.default_profiles.desktops.gnome import GnomeFlavor, GnomeProfile
from archinstall.default_profiles.profile import CustomSetting


def test_gnome_profile_defaults_to_minimal() -> None:
	profile = GnomeProfile()

	assert profile._selected_flavor() == GnomeFlavor.Minimal
	assert profile.packages == GnomeFlavor.Minimal.packages()


def test_gnome_profile_full_flavor() -> None:
	profile = GnomeProfile()
	profile.custom_settings[CustomSetting.GnomeFlavor] = GnomeFlavor.Full.value

	assert profile._selected_flavor() == GnomeFlavor.Full
	assert profile.packages == GnomeFlavor.Full.packages()


def test_gnome_profile_minimal_flavor() -> None:
	profile = GnomeProfile()
	profile.custom_settings[CustomSetting.GnomeFlavor] = GnomeFlavor.Minimal.value

	assert profile._selected_flavor() == GnomeFlavor.Minimal
	assert profile.packages == GnomeFlavor.Minimal.packages()
