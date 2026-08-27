import asyncio

from pytest import MonkeyPatch

from archinstall.lib.disk.disk_menu import DiskLayoutConfigurationMenu, select_lvm_config
from archinstall.lib.menu.helpers import Confirmation, Selection
from archinstall.lib.models.device import DiskLayoutConfiguration, DiskLayoutType, LvmConfiguration, LvmLayoutType
from archinstall.tui.result import Result


def test_lvm_status_is_visible_when_unconfigured() -> None:
	menu = DiskLayoutConfigurationMenu(None)
	item = menu._item_group.find_by_key('lvm_config')

	assert item.text == 'LVM'
	assert item.preview_action is not None
	assert item.preview_action(item) == 'LVM: Not configured'


def test_lvm_status_names_configured_layout() -> None:
	preset = LvmConfiguration(config_type=LvmLayoutType.Default, vol_groups=[])
	disk_config = DiskLayoutConfiguration(config_type=DiskLayoutType.Default, lvm_config=preset)
	menu = DiskLayoutConfigurationMenu(disk_config)
	item = menu._item_group.find_by_key('lvm_config')

	assert item.text == 'LVM'
	assert item.preview_action is not None
	preview = item.preview_action(item)
	assert isinstance(preview, str)
	assert 'Configuration: Default layout' in preview


def test_lvm_menu_exposes_none_default_and_back(monkeypatch: MonkeyPatch) -> None:
	seen: list[Selection[str]] = []

	async def show(selection: Selection[str]) -> Result[str]:
		seen.append(selection)
		return Result.selection('Back')

	monkeypatch.setattr(Selection, 'show', show)
	preset = LvmConfiguration(config_type=LvmLayoutType.Default, vol_groups=[])
	disk_config = DiskLayoutConfiguration(config_type=DiskLayoutType.Default)

	assert asyncio.run(select_lvm_config(disk_config, preset)) is preset
	assert [item.text for item in seen[0]._group.items] == [
		'Do not use LVM',
		LvmLayoutType.Default.display_msg(),
		'Back',
	]
	assert seen[0]._group.focus_item is not None
	assert seen[0]._group.focus_item.value == LvmLayoutType.Default.display_msg()


def test_disabling_existing_lvm_requires_confirmation(monkeypatch: MonkeyPatch) -> None:
	async def select_none(_selection: Selection[str]) -> Result[str]:
		return Result.selection('Do not use LVM')

	async def decline(_confirmation: Confirmation) -> Result[bool]:
		return Result.false()

	monkeypatch.setattr(Selection, 'show', select_none)
	monkeypatch.setattr(Confirmation, 'show', decline)
	preset = LvmConfiguration(config_type=LvmLayoutType.Default, vol_groups=[])
	disk_config = DiskLayoutConfiguration(config_type=DiskLayoutType.Default)

	assert asyncio.run(select_lvm_config(disk_config, preset)) is preset


def test_confirming_disable_clears_existing_lvm(monkeypatch: MonkeyPatch) -> None:
	async def select_none(_selection: Selection[str]) -> Result[str]:
		return Result.selection('Do not use LVM')

	async def confirm(_confirmation: Confirmation) -> Result[bool]:
		return Result.true()

	monkeypatch.setattr(Selection, 'show', select_none)
	monkeypatch.setattr(Confirmation, 'show', confirm)
	preset = LvmConfiguration(config_type=LvmLayoutType.Default, vol_groups=[])
	disk_config = DiskLayoutConfiguration(config_type=DiskLayoutType.Default)

	assert asyncio.run(select_lvm_config(disk_config, preset)) is None
