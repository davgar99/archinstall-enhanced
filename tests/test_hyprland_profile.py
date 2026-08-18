from archinstall.default_profiles.desktops.hyprland import HyprlandProfile


def test_hyprland_profile_uses_current_hyprland_packages() -> None:
	packages = HyprlandProfile().packages

	for package in ('hyprlauncher', 'hyprpolkitagent', 'wl-clipboard', 'hyprpaper', 'waybar', 'quickshell'):
		assert package in packages

	assert 'wofi' not in packages
	assert 'polkit-kde-agent' not in packages
