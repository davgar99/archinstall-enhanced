import re
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

from archinstall.lib.exceptions import DiskError, SysCallError
from archinstall.lib.log import debug
from archinstall.lib.models.bootloader import Bootloader
from archinstall.lib.models.device import DiskLayoutConfiguration, FilesystemType, SnapshotType

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


def _btrfs_snapshot_mountpoints(disk_config: DiskLayoutConfiguration) -> list[Path]:
	mountpoints: set[Path] = set()
	for modification in disk_config.device_modifications:
		for partition in modification.partitions:
			if partition.fs_type != FilesystemType.BTRFS:
				continue
			if partition.mountpoint in {Path('/'), Path('/home')}:
				mountpoints.add(partition.mountpoint)
			for subvolume in partition.btrfs_subvols:
				if subvolume.mountpoint in {Path('/'), Path('/home')}:
					mountpoints.add(subvolume.mountpoint)

	if disk_config.lvm_config:
		for volume in disk_config.lvm_config.get_all_volumes():
			if volume.fs_type != FilesystemType.BTRFS:
				continue
			if volume.mountpoint in {Path('/'), Path('/home')}:
				mountpoints.add(volume.mountpoint)
			for subvolume in volume.btrfs_subvols:
				if subvolume.mountpoint in {Path('/'), Path('/home')}:
					mountpoints.add(subvolume.mountpoint)

	return sorted(mountpoints, key=lambda path: (path != Path('/'), str(path)))


def _register_config_name(target: Path, name: str) -> None:
	global_config = target / 'etc/conf.d/snapper'
	global_config.parent.mkdir(parents=True, exist_ok=True)
	content = global_config.read_text() if global_config.exists() else 'SNAPPER_CONFIGS=""\n'
	match = re.search(r'^SNAPPER_CONFIGS=(?:"([^"]*)"|([^\n]*))$', content, flags=re.MULTILINE)
	current: list[str] = []
	if match:
		current = (match.group(1) or match.group(2) or '').split()
	if name not in current:
		current.append(name)
	new_line = f'SNAPPER_CONFIGS="{" ".join(current)}"'
	if match:
		content = content[: match.start()] + new_line + content[match.end() :]
	else:
		content = content.rstrip() + '\n' + new_line + '\n'
	global_config.write_text(content)


def _write_snapper_config_for_existing_subvolume(target: Path, name: str, mountpoint: Path) -> None:
	config_path = target / 'etc/snapper/configs' / name
	if config_path.exists():
		_register_config_name(target, name)
		return

	template_candidates = [
		target / 'etc/snapper/config-templates/default',
		target / 'usr/share/snapper/config-templates/default',
	]
	template = next((candidate for candidate in template_candidates if candidate.exists()), None)
	if template is None:
		raise DiskError('Snapper default configuration template is missing')

	content = template.read_text()
	subvolume_line = f'SUBVOLUME="{mountpoint}"'
	if re.search(r'^SUBVOLUME=', content, flags=re.MULTILINE):
		content = re.sub(r'^SUBVOLUME=.*$', subvolume_line, content, count=1, flags=re.MULTILINE)
	else:
		content = subvolume_line + '\n' + content

	config_path.parent.mkdir(parents=True, exist_ok=True)
	config_path.write_text(content)
	_register_config_name(target, name)


def _setup_snapper_config(installation: Installer, name: str, mountpoint: Path) -> None:
	target_mountpoint = installation.target / mountpoint.relative_to('/')
	snapshots_path = target_mountpoint / '.snapshots'
	config_path = installation.target / 'etc/snapper/configs' / name

	if config_path.exists():
		debug(f'Snapper configuration {name} already exists; preserving it')
		_register_config_name(installation.target, name)
		return

	if snapshots_path.exists():
		debug(f'Using existing Snapper snapshot subvolume at {snapshots_path}')
		_write_snapper_config_for_existing_subvolume(installation.target, name, mountpoint)
		return

	command = f'snapper --no-dbus -c {shlex.quote(name)} create-config {shlex.quote(str(mountpoint))}'
	try:
		installation.arch_chroot(command, peek_output=True)
	except SysCallError as err:
		raise DiskError(f'Could not setup Btrfs Snapper configuration {name}: {err}') from err


def setup_btrfs_snapshot_safe(
	installation: Installer,
	disk_config: DiskLayoutConfiguration,
	snapshot_type: SnapshotType,
	bootloader: Bootloader | None = None,
) -> None:
	if snapshot_type != SnapshotType.Snapper:
		installation.setup_btrfs_snapshot(snapshot_type, bootloader)
		return

	debug('Setting up Btrfs Snapper with manual-layout compatibility')
	installation.pacman.strap('snapper')

	for mountpoint in _btrfs_snapshot_mountpoints(disk_config):
		name = 'root' if mountpoint == Path('/') else 'home'
		_setup_snapper_config(installation, name, mountpoint)

	installation.enable_service('snapper-timeline.timer')
	installation.enable_service('snapper-cleanup.timer')

	if bootloader == Bootloader.Grub:
		installation.pacman.strap('grub-btrfs')
		installation.pacman.strap('inotify-tools')
		installation._configure_grub_btrfsd(snapshot_type)
		installation.enable_service('grub-btrfsd.service')
