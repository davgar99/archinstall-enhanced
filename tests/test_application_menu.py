from archinstall.lib.applications.application_menu import ApplicationMenu
from archinstall.lib.models.application import ApplicationConfiguration


def test_aur_helper_is_not_available_in_application_menu() -> None:
	keys = {item.key for item in ApplicationMenu()._item_group.items}
	assert 'aur_helper_config' not in keys


def test_legacy_aur_helper_configuration_is_ignored() -> None:
	config = ApplicationConfiguration.parse_arg({'aur_helper_config': {'aur_helper': 'yay'}})

	assert 'aur_helper_config' not in config.json()
	assert all('AUR' not in line for line in config.summary())
