from archinstall.lib.log import debug
from archinstall.lib.models.device import DiskLayoutConfiguration


def discard_stale_btrfs_subvolumes_for_wipe(disk_config: DiskLayoutConfiguration) -> int:
	"""Drop discovered Btrfs subvolumes that cannot be mounted on devices being wiped.

	A whole-device wipe makes pre-existing subvolume metadata irrelevant. Keeping an
	old entry whose mountpoint is unknown can later make mount ordering call
	``relative_mountpoint`` and raise before the requested format takes place.

	Planned subvolumes with real mountpoints are retained.
	"""
	removed = 0
	for device_modification in disk_config.device_modifications:
		if not device_modification.wipe:
			continue

		for partition in device_modification.partitions:
			before = len(partition.btrfs_subvols)
			partition.btrfs_subvols = [subvolume for subvolume in partition.btrfs_subvols if subvolume.mountpoint is not None]
			removed += before - len(partition.btrfs_subvols)

	if removed:
		debug(f'Discarded {removed} stale Btrfs subvolume entries before requested disk wipe')
	return removed
