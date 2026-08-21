from archinstall.default_profiles.profile import Profile, ProfileType
from archinstall.lib.models.profile import ProfileConfiguration


def test_profile_summary_includes_selected_desktop() -> None:
	plasma = Profile('Plasma', ProfileType.DesktopEnv)
	desktop = Profile('Desktop', ProfileType.Desktop, current_selection=[plasma])
	config = ProfileConfiguration(profile=desktop)

	assert config.summary() == ['Desktop', 'Plasma']


def test_profile_summary_includes_opencl_selection() -> None:
	desktop = Profile('Desktop', ProfileType.Desktop)
	config = ProfileConfiguration(profile=desktop, install_opencl=True)

	assert config.summary() == ['Desktop', 'OpenCL support: Enabled']
