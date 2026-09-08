from archinstall.default_profiles.desktop import desktop_profiles_for_mode
from archinstall.default_profiles.profile import DisplayServerType, Profile, ProfileType


def test_wayland_first_filters_xorg_only_profiles() -> None:
	wayland = Profile('Wayland desktop', ProfileType.DesktopEnv, display_server=DisplayServerType.Wayland)
	xorg = Profile('Xorg desktop', ProfileType.DesktopEnv, display_server=DisplayServerType.Xorg)

	assert desktop_profiles_for_mode([wayland, xorg], include_xorg=False) == [wayland]


def test_compatibility_mode_preserves_xorg_profiles() -> None:
	wayland = Profile('Wayland desktop', ProfileType.DesktopEnv, display_server=DisplayServerType.Wayland)
	xorg = Profile('Xorg desktop', ProfileType.DesktopEnv, display_server=DisplayServerType.Xorg)

	assert desktop_profiles_for_mode([wayland, xorg], include_xorg=True) == [wayland, xorg]
