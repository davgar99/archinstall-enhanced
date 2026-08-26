import asyncio

from pytest import MonkeyPatch

from archinstall.lib.disk.disk_menu import select_mount_options
from archinstall.lib.menu.helpers import Selection
from archinstall.lib.models.device import BtrfsMountOption
from archinstall.tui.result import Result


def test_automatic_btrfs_options_default_to_zstd_compression(monkeypatch: MonkeyPatch) -> None:
	async def skip_selection(selection: Selection[str]) -> Result[str]:
		assert selection._group.default_item is not None
		assert selection._group.default_item.value == BtrfsMountOption.compress.value
		return Result.skip()

	monkeypatch.setattr(Selection, 'show', skip_selection)

	assert asyncio.run(select_mount_options()) == [BtrfsMountOption.compress.value]
