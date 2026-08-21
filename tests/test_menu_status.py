from archinstall.tui.menu_item import MenuItem, MenuItemGroup


class _FakeAuthConfig:
	def __init__(self, *, root_password: bool = False, superuser: bool = False) -> None:
		self.root_enc_password = object() if root_password else None
		self._superuser = superuser

	def has_superuser(self) -> bool:
		return self._superuser


def _global_menu_group(*items: MenuItem) -> MenuItemGroup:
	return MenuItemGroup(
		[
			*items,
			MenuItem('Install', key='__config___install'),
		],
	)


def test_status_indicator_marks_missing_required_field() -> None:
	disk = MenuItem('Disk configuration', key='disk_config', mandatory=True)
	packages = MenuItem('Additional packages', value=[], key='packages')
	group = _global_menu_group(disk, packages)

	items = {item.key: item for item in group.get_enabled_items()}

	assert items['disk_config'].text.startswith('[bold yellow]![/bold yellow] ')
	assert items['packages'].text == '  Additional packages'
	assert items['__config___install'].text == 'Install'


def test_status_indicator_clears_when_required_field_is_configured() -> None:
	kernels = MenuItem('Kernels', value=['linux'], key='kernels', mandatory=True)
	group = _global_menu_group(kernels)

	items = {item.key: item for item in group.get_enabled_items()}

	assert items['kernels'].text == '  Kernels'


def test_authentication_indicator_matches_install_requirement() -> None:
	auth = MenuItem('Authentication', value=_FakeAuthConfig(), key='auth_config')
	group = _global_menu_group(auth)

	items = {item.key: item for item in group.get_enabled_items()}
	assert items['auth_config'].text.startswith('[bold yellow]![/bold yellow] ')

	auth.value = _FakeAuthConfig(superuser=True)
	items = {item.key: item for item in group.get_enabled_items()}
	assert items['auth_config'].text == '  Authentication'

	auth.value = _FakeAuthConfig(root_password=True)
	items = {item.key: item for item in group.get_enabled_items()}
	assert items['auth_config'].text == '  Authentication'


def test_status_rendering_does_not_mutate_menu_items() -> None:
	disk = MenuItem('Disk configuration', key='disk_config', mandatory=True)
	group = _global_menu_group(disk)

	first = {item.key: item for item in group.get_enabled_items()}
	second = {item.key: item for item in group.get_enabled_items()}

	assert first['disk_config'].text == second['disk_config'].text
	assert disk.text == 'Disk configuration'


def test_status_rendering_preserves_focus_lookup() -> None:
	disk = MenuItem('Disk configuration', key='disk_config', mandatory=True)
	packages = MenuItem('Additional packages', key='packages')
	group = _global_menu_group(disk, packages)
	group.focus_item = packages

	assert group.get_focused_index() == 1


def test_status_rendering_preserves_focus_lookup_for_keyless_item() -> None:
	disk = MenuItem('Disk configuration', key='disk_config', mandatory=True)
	separator = MenuItem('', read_only=True)
	group = _global_menu_group(disk, separator)

	first_pass = group.get_enabled_items()
	group.focus_item = first_pass[1]

	group.get_enabled_items()
	assert group.get_focused_index() == 1


def test_regular_submenus_are_unchanged() -> None:
	optional = MenuItem('Plymouth', key='plymouth')
	group = MenuItemGroup([optional])

	assert group.get_enabled_items()[0].text == 'Plymouth'
