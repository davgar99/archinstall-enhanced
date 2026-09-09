from pathlib import Path

from archinstall.lib.command import SysCommand
from archinstall.lib.log import debug, info
from archinstall.lib.models.device import (
	DiskLayoutConfiguration,
	DiskLayoutType,
	EncryptionType,
	FilesystemType,
	LvmVolume,
	PartitionModification,
)


def _best_effort(command: list[str], description: str) -> bool:
	try:
		SysCommand(command)
		return True
	except Exception as err:
		debug(f'Cleanup skipped while {description}: {err}')
		return False


def _mapper_path(device: PartitionModification | LvmVolume) -> Path | None:
	mapper_name = device.mapper_name
	return Path('/dev/mapper') / mapper_name if mapper_name else None


def _swap_paths(disk_config: DiskLayoutConfiguration) -> list[Path]:
	encryption = disk_config.disk_encryption
	paths: list[Path] = []

	for device_modification in disk_config.device_modifications:
		for partition in device_modification.partitions:
			if partition.fs_type != FilesystemType.LINUX_SWAP:
				continue
			path = _mapper_path(partition) if encryption and partition in encryption.partitions else partition.dev_path
			if path:
				paths.append(path)

	if disk_config.lvm_config:
		for volume in disk_config.lvm_config.get_all_volumes():
			if volume.fs_type != FilesystemType.LINUX_SWAP:
				continue
			path = _mapper_path(volume) if encryption and volume in encryption.lvm_volumes else volume.dev_path
			if path:
				paths.append(path)

	return list(dict.fromkeys(paths))


def _close_luks_devices(disk_config: DiskLayoutConfiguration, *, partitions: bool, volumes: bool) -> None:
	encryption = disk_config.disk_encryption
	if not encryption or encryption.encryption_type == EncryptionType.NO_ENCRYPTION:
		return

	devices: list[PartitionModification | LvmVolume] = []
	if partitions:
		devices.extend(encryption.partitions)
	if volumes:
		devices.extend(encryption.lvm_volumes)

	for device in reversed(devices):
		if device.mapper_name:
			_best_effort(['cryptsetup', 'close', device.mapper_name], f'closing LUKS mapping {device.mapper_name}')


def _deactivate_lvm(disk_config: DiskLayoutConfiguration) -> None:
	if not disk_config.lvm_config:
		return

	for volume_group in reversed(disk_config.lvm_config.vol_groups):
		_best_effort(['vgchange', '-an', volume_group.name], f'deactivating volume group {volume_group.name}')


def teardown_installation(target: Path, disk_config: DiskLayoutConfiguration) -> None:
	"""Release storage resources created by the guided installer.

	Pre-mounted configurations stay user-owned and are intentionally untouched.
	Other cleanup is best-effort so it never hides the original installation error.
	"""
	if disk_config.config_type == DiskLayoutType.Pre_mount:
		debug('Skipping teardown for user-managed pre-mounted storage')
		return

	info('Cleaning up installation storage resources')

	for swap_path in _swap_paths(disk_config):
		_best_effort(['swapoff', str(swap_path)], f'disabling swap on {swap_path}')

	_best_effort(['umount', '--recursive', str(target)], f'unmounting {target}')

	encryption = disk_config.disk_encryption
	enc_type = encryption.encryption_type if encryption else EncryptionType.NO_ENCRYPTION

	if enc_type == EncryptionType.LUKS_ON_LVM:
		_close_luks_devices(disk_config, partitions=False, volumes=True)
		_deactivate_lvm(disk_config)
	elif enc_type == EncryptionType.LVM_ON_LUKS:
		_deactivate_lvm(disk_config)
		_close_luks_devices(disk_config, partitions=True, volumes=False)
	else:
		_close_luks_devices(disk_config, partitions=True, volumes=True)
		_deactivate_lvm(disk_config)
