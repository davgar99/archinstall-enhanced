import pytest

from archinstall.lib.args import ArchConfig
from archinstall.lib.global_menu import GlobalMenu
from archinstall.lib.hardware import SysInfo
from archinstall.lib.models.network import NetworkConfiguration, NicType
from archinstall.tui.components import _menu_prompt
from archinstall.tui.menu_item import MenuItem, MenuItemGroup, MenuItemRole, MenuItemState, MsgLevelType, PreviewResult


class _FakeAuthConfig:
	def __init__(self, *, root_password: bool = False, superuser: bool = False, regular_user: bool = False) -> None:
		self.root_enc_password = object() if root_password else None
		self._superuser = superuser
		self._regular_user = regular_user

	def has_superuser(self) -> bool:
		return self._superuser

	def has_regular_user(self) -> bool:
		return self._regular_user


@pytest.fixture
def menu_under_test(monkeypatch: pytest.MonkeyPatch) -> GlobalMenu:
	monkeypatch.setattr(SysInfo, 'has_uefi', staticmethod(lambda: False))
	monkeypatch.setattr(SysInfo, 'has_windows_bootloader', staticmethod(lambda: False))
	return GlobalMenu(ArchConfig(), skip_boot=True)


def _rendered_items(menu: GlobalMenu) -> dict[str, MenuItem]:
	return {item.key: item for item in menu._item_group.get_enabled_items() if item.key is not None}


def test_master_markers_and_two_column_gutter() -> None:
	items = [
		MenuItem('Configured', state=MenuItemState.COMPLETE),
		MenuItem('Warning', state=MenuItemState.WARNING),
		MenuItem('Blocking', state=MenuItemState.BLOCKING),
		MenuItem('Optional', state=MenuItemState.OPTIONAL_UNSET),
	]
	assert [_menu_prompt(item).plain for item in items] == [
		'  Configured',
		'! Warning',
		'! Blocking',
		'  Optional',
	]
	assert all('bright_yellow' in str(_menu_prompt(item).spans[0].style) for item in items[1:3])
	assert [item.text for item in items] == ['Configured', 'Warning', 'Blocking', 'Optional']


def test_section_has_one_leading_row_and_information_does_not() -> None:
	section = MenuItem('Section', role=MenuItemRole.SECTION)
	information = MenuItem('Information', role=MenuItemRole.INFORMATION)
	assert _menu_prompt(section).plain == '\nSection'
	assert _menu_prompt(section).plain.count('\n') == 1
	assert _menu_prompt(information).plain == 'Information'


def test_state_provider_does_not_mutate_filterable_text() -> None:
	item = MenuItem('Disk configuration', key='disk_config')
	group = MenuItemGroup([item], state_provider=lambda _item: MenuItemState.BLOCKING)
	displayed = group.get_enabled_items()[0]
	assert displayed.state is MenuItemState.BLOCKING
	assert displayed.text == 'Disk configuration'
	assert item.state is MenuItemState.NEUTRAL
	group.set_filter_pattern('disk configuration')
	assert group.get_enabled_items()[0].get_id() == item.get_id()


def test_required_authentication_and_kernels_are_blocking(menu_under_test: GlobalMenu) -> None:
	menu_under_test._item_group.find_by_key('kernels').value = []
	items = _rendered_items(menu_under_test)
	assert items['disk_config'].state is MenuItemState.BLOCKING
	assert items['kernels'].state is MenuItemState.BLOCKING
	assert items['auth_config'].state is MenuItemState.BLOCKING
	assert _menu_prompt(items['disk_config']).plain == '! Disk configuration'
	assert menu_under_test.is_config_valid() is False


def test_authentication_transitions_to_complete(menu_under_test: GlobalMenu) -> None:
	auth = menu_under_test._item_group.find_by_key('auth_config')
	auth.value = _FakeAuthConfig(superuser=True)
	assert menu_under_test._item_state(auth) is MenuItemState.COMPLETE
	auth.value = _FakeAuthConfig(root_password=True)
	assert menu_under_test._item_state(auth) is MenuItemState.COMPLETE


def test_desktop_greeter_requires_regular_user(menu_under_test: GlobalMenu) -> None:
	from archinstall.default_profiles.profile import GreeterType

	class Selection:
		default_greeter_type = GreeterType.Sddm

	class Profile:
		def __init__(self) -> None:
			self.current_selection = [Selection()]

		def is_desktop_profile(self) -> bool:
			return True

	class ProfileConfig:
		profile = Profile()

	menu_under_test._item_group.find_by_key('profile_config').value = ProfileConfig()
	menu_under_test._item_group.find_by_key('auth_config').value = _FakeAuthConfig(superuser=True)
	assert any('regular user' in issue for issue in menu_under_test.blocking_issues())


def test_network_is_warning_not_blocking(menu_under_test: GlobalMenu) -> None:
	network = menu_under_test._item_group.find_by_key('network_config')
	initial_count = len(menu_under_test.blocking_issues())
	assert menu_under_test._item_state(network) is MenuItemState.WARNING
	assert len(menu_under_test.blocking_issues()) == initial_count
	assert _menu_prompt(_rendered_items(menu_under_test)['network_config']).plain.startswith('!')
	network.value = NetworkConfiguration(NicType.ISO)
	assert menu_under_test._item_state(network) is MenuItemState.COMPLETE


def test_bootloader_issue_drives_preview_and_final_guard(menu_under_test: GlobalMenu, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(menu_under_test, '_validate_bootloader', lambda: 'Invalid bootloader layout')
	bootloader = menu_under_test._item_group.find_by_key('bootloader_config')
	assert menu_under_test._item_state(bootloader) is MenuItemState.BLOCKING
	assert 'Invalid bootloader layout' in menu_under_test.blocking_issues()
	preview = menu_under_test._prev_install_invalid_config(menu_under_test._item_group.find_by_key('__config___install'))
	assert isinstance(preview, PreviewResult)
	assert any(level is MsgLevelType.MsgError and 'Invalid bootloader layout' in message for message, level in preview.messages)


def test_status_rendering_preserves_focus_and_empty_filter_recovery() -> None:
	alpha = MenuItem('Alpha', value=1)
	beta = MenuItem('Beta', value=2)
	group = MenuItemGroup([alpha, beta], focus_item=beta, state_provider=lambda _item: MenuItemState.COMPLETE)
	assert group.get_focused_index() == 1
	group.set_filter_pattern('no match')
	assert group.focus_item is None
	group.set_filter_pattern('')
	assert group.focus_item is beta
