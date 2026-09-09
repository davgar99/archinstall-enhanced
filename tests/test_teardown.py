from pathlib import Path
from types import SimpleNamespace

from pytest import MonkeyPatch

from archinstall.lib.disk import teardown
from archinstall.lib.models.device import DiskLayoutType, EncryptionType, FilesystemType


def test_lvm_on_luks_teardown_deactivates_lvm_before_closing_container(monkeypatch: MonkeyPatch) -> None:
	commands: list[list[str]] = []

	def record_command(command: list[str], description: str) -> bool:
		commands.append(command)
		return True

	monkeypatch.setattr(teardown, '_best_effort', record_command)

	partition = SimpleNamespace(
		fs_type=FilesystemType.LINUX_SWAP,
		mapper_name='cryptlvm',
		dev_path=Path('/dev/sda2'),
	)
	encryption = SimpleNamespace(
		encryption_type=EncryptionType.LVM_ON_LUKS,
		partitions=[partition],
		lvm_volumes=[],
	)
	lvm_config = SimpleNamespace(
		vol_groups=[SimpleNamespace(name='vg0')],
		get_all_volumes=list,
	)
	config = SimpleNamespace(
		config_type=DiskLayoutType.Manual,
		disk_encryption=encryption,
		device_modifications=[SimpleNamespace(partitions=[partition])],
		lvm_config=lvm_config,
	)

	teardown.teardown_installation(Path('/mnt'), config)  # type: ignore[arg-type]

	assert commands[0] == ['swapoff', '/dev/mapper/cryptlvm']
	assert commands[1] == ['umount', '--recursive', '/mnt']
	assert commands[2] == ['vgchange', '-an', 'vg0']
	assert commands[3] == ['cryptsetup', 'close', 'cryptlvm']


def test_pre_mounted_config_is_not_torn_down(monkeypatch: MonkeyPatch) -> None:
	commands: list[list[str]] = []

	def record_command(command: list[str], description: str) -> bool:
		commands.append(command)
		return True

	monkeypatch.setattr(teardown, '_best_effort', record_command)
	config = SimpleNamespace(config_type=DiskLayoutType.Pre_mount)

	teardown.teardown_installation(Path('/mnt/custom'), config)  # type: ignore[arg-type]
	assert commands == []
