from types import SimpleNamespace

from archinstall.lib.disk.btrfs_safety import discard_stale_btrfs_subvolumes_for_wipe


def test_stale_btrfs_entries_are_removed_only_for_wiped_devices() -> None:
	stale = SimpleNamespace(mountpoint=None)
	root = SimpleNamespace(mountpoint='/')
	wiped_partition = SimpleNamespace(btrfs_subvols=[stale, root])
	preserved_partition = SimpleNamespace(btrfs_subvols=[stale])
	config = SimpleNamespace(
		device_modifications=[
			SimpleNamespace(wipe=True, partitions=[wiped_partition]),
			SimpleNamespace(wipe=False, partitions=[preserved_partition]),
		]
	)

	removed = discard_stale_btrfs_subvolumes_for_wipe(config)  # type: ignore[arg-type]

	assert removed == 1
	assert wiped_partition.btrfs_subvols == [root]
	assert preserved_partition.btrfs_subvols == [stale]
