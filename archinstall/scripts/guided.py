import subprocess
import sys
import time
import traceback
from dataclasses import dataclass

from archinstall.applications.graphics_extras import GraphicsExtrasApp
from archinstall.applications.virtualbox_guest import VirtualBoxGuestApp
from archinstall.lib.applications.application_handler import ApplicationHandler
from archinstall.lib.args import ArchConfig, ArchConfigHandler
from archinstall.lib.authentication.authentication_handler import AuthenticationHandler
from archinstall.lib.bootloader.os_prober import prepare_grub_os_prober
from archinstall.lib.bootloader.utils import validate_bootloader_layout
from archinstall.lib.configuration import confirm_config
from archinstall.lib.disk.filesystem import FilesystemHandler
from archinstall.lib.disk.utils import disk_layouts
from archinstall.lib.gaming.gaming_handler import GamingHandler
from archinstall.lib.general.general_menu import PostInstallationAction, select_post_installation
from archinstall.lib.global_menu import GlobalMenu
from archinstall.lib.hardware import GfxDriver
from archinstall.lib.installer import Installer, accessibility_tools_in_use, run_custom_user_commands
from archinstall.lib.log import debug, error, info, logger
from archinstall.lib.menu.helpers import Notify
from archinstall.lib.menu.util import delayed_warning
from archinstall.lib.mirror.mirror_handler import MirrorListHandler
from archinstall.lib.models import Bootloader
from archinstall.lib.models.device import DiskLayoutType, EncryptionType
from archinstall.lib.models.packages import Repository
from archinstall.lib.models.users import User
from archinstall.lib.network.network_handler import install_network_config
from archinstall.lib.network.regulatory import configure_wireless_regulatory
from archinstall.lib.packages.util import check_version_upgrade
from archinstall.lib.profile.profiles_handler import profile_handler
from archinstall.lib.translationhandler import tr
from archinstall.tui.components import tui
from archinstall.tui.presentation import Activity, ActivityReporter, InstallationOutcome


def show_menu(
	arch_config_handler: ArchConfigHandler,
	mirror_list_handler: MirrorListHandler,
) -> None:
	upgrade = check_version_upgrade()
	title_text = 'Archinstall Enhanced'

	if upgrade:
		text = tr('New version available') + f': {upgrade}'
		title_text += f' ({text})'

	global_menu = GlobalMenu(
		arch_config_handler.config,
		mirror_list_handler,
		arch_config_handler.args.skip_boot,
		advanced=arch_config_handler.args.advanced,
		title=title_text,
	)

	result: ArchConfig | None = tui.run(global_menu)
	if result is None:
		sys.exit(0)


@dataclass(frozen=True)
class _InstallationSession:
	outcome: InstallationOutcome
	installation: Installer


def _perform_installation_core(
	arch_config_handler: ArchConfigHandler,
	mirror_list_handler: MirrorListHandler,
	auth_handler: AuthenticationHandler,
	application_handler: ApplicationHandler,
	gaming_handler: GamingHandler,
	reporter: ActivityReporter | None = None,
) -> _InstallationSession:
	start_time = time.monotonic()
	info('Starting installation...')
	config = arch_config_handler.config
	if not config.disk_config:
		raise ValueError('No disk configuration provided')

	disk_config = config.disk_config
	mountpoint = disk_config.mountpoint or arch_config_handler.args.mountpoint
	optional_repositories = list(config.mirror_config.optional_repositories) if config.mirror_config else []
	if config.gaming_config and config.gaming_config.requires_multilib() and Repository.Multilib not in optional_repositories:
		optional_repositories.append(Repository.Multilib)

	stage_labels = [
		tr('Storage and mount validation'),
		tr('Encryption and mirrors'),
		tr('Base installation'),
		tr('Bootloader'),
		tr('Networking and accounts'),
		tr('System services and gaming'),
		tr('Profiles and packages'),
		tr('System settings'),
		tr('Post-install hooks'),
		tr('Final validation and log sync'),
	]
	stage_number = 0
	failed_stage = tr('Preparing installation')

	def set_stage(label: str) -> None:
		nonlocal stage_number, failed_stage
		failed_stage = label
		stage_number += 1
		if reporter:
			reporter.set_stage(label, stage_number, len(stage_labels))

	try:
		set_stage(stage_labels[0])
		FilesystemHandler(disk_config).perform_filesystem_operations()
		with Installer(mountpoint, disk_config, kernels=config.kernels, silent=arch_config_handler.args.silent) as installation:
			if disk_config.config_type != DiskLayoutType.Pre_mount:
				installation.mount_ordered_layout()
			installation.sanity_check(
				arch_config_handler.args.offline,
				arch_config_handler.args.skip_ntp,
				arch_config_handler.args.skip_wkd,
			)

			set_stage(stage_labels[1])
			if (
				disk_config.config_type != DiskLayoutType.Pre_mount
				and disk_config.disk_encryption
				and disk_config.disk_encryption.encryption_type != EncryptionType.NO_ENCRYPTION
			):
				installation.generate_key_files()
			if mirror_config := config.mirror_config:
				installation.set_mirrors(mirror_list_handler, mirror_config, on_target=False)

			set_stage(stage_labels[2])
			installation.minimal_installation(
				optional_repositories=optional_repositories,
				mkinitcpio=not config.bootloader_config or not config.bootloader_config.uki,
				hostname=config.hostname,
				locale_config=config.locale_config,
				pacman_config=config.pacman_config,
			)
			if mirror_config := config.mirror_config:
				installation.set_mirrors(mirror_list_handler, mirror_config, on_target=True)
			if config.swap and config.swap.enabled:
				installation.setup_swap(algo=config.swap.algorithm)

			set_stage(stage_labels[3])
			if config.bootloader_config and config.bootloader_config.bootloader != Bootloader.NO_BOOTLOADER:
				prepare_grub_os_prober(installation, config.bootloader_config.bootloader, config.bootloader_config.os_prober)
				installation.add_bootloader(
					config.bootloader_config.bootloader,
					config.bootloader_config.uki,
					config.bootloader_config.removable,
					config.bootloader_config.plymouth,
				)

			set_stage(stage_labels[4])
			if config.network_config:
				install_network_config(config.network_config, installation, config.profile_config)
			users = None
			if config.auth_config:
				if config.auth_config.users:
					users = config.auth_config.users
					installation.create_users(users)
				auth_handler.setup_auth(installation, config.auth_config, config.hostname)

			set_stage(stage_labels[5])
			if app_config := config.app_config:
				application_handler.install_applications(installation, app_config, users, config.network_config)
			if gaming_config := config.gaming_config:
				gaming_handler.install_gaming(installation, gaming_config, users)
			gfx_driver = config.profile_config.gfx_driver if config.profile_config else None
			install_32bit = bool(config.gaming_config and config.gaming_config.install_32bit_graphics)
			install_opencl = bool(config.profile_config and config.profile_config.install_opencl)
			GraphicsExtrasApp().install(installation, install_32bit, install_opencl, gfx_driver)

			set_stage(stage_labels[6])
			if profile_config := config.profile_config:
				profile_handler.install_profile_config(installation, profile_config)
			if VirtualBoxGuestApp.detected():
				package_in_profile = bool(config.profile_config and config.profile_config.gfx_driver == GfxDriver.VMOpenSource)
				VirtualBoxGuestApp().install(installation, users, install_package=not package_in_profile)
			if config.packages and config.packages[0] != '':
				installation.add_additional_packages(config.packages)

			set_stage(stage_labels[7])
			if timezone := config.timezone:
				installation.set_timezone(timezone)
				configure_wireless_regulatory(installation, timezone)
			if config.hardware_clock_utc is not False:
				installation.set_hardware_clock_utc()
			if config.ntp:
				installation.activate_time_synchronization()
			if accessibility_tools_in_use():
				installation.enable_espeakup()
			if config.auth_config and config.auth_config.root_enc_password:
				installation.set_user_password(User('root', config.auth_config.root_enc_password, False))

			set_stage(stage_labels[8])
			if (profile_config := config.profile_config) and profile_config.profile:
				profile_config.profile.post_install(installation)
				if users:
					profile_config.profile.provision(installation, users)
			if services := config.services:
				installation.enable_service(services)
			if disk_config.has_default_btrfs_vols():
				btrfs_options = disk_config.btrfs_options
				snapshot_config = btrfs_options.snapshot_config if btrfs_options else None
				if snapshot_config and snapshot_config.snapshot_type:
					bootloader = config.bootloader_config.bootloader if config.bootloader_config else None
					installation.setup_btrfs_snapshot(snapshot_config.snapshot_type, bootloader)
			if commands := config.custom_commands:
				run_custom_user_commands(commands, installation)

			set_stage(stage_labels[9])
			installation.genfstab()
			debug(f'Disk states after installing:\n{disk_layouts()}')

		outcome = InstallationOutcome(time.monotonic() - start_time, mountpoint, logger.path)
		return _InstallationSession(outcome, installation)
	except BaseException as exception:
		exception.add_note(f'Archinstall stage: {failed_stage}')
		raise


def perform_installation(
	arch_config_handler: ArchConfigHandler,
	mirror_list_handler: MirrorListHandler,
	auth_handler: AuthenticationHandler,
	application_handler: ApplicationHandler,
	gaming_handler: GamingHandler,
) -> InstallationOutcome:
	def operation(reporter: ActivityReporter | None) -> _InstallationSession:
		return _perform_installation_core(
			arch_config_handler,
			mirror_list_handler,
			auth_handler,
			application_handler,
			gaming_handler,
			reporter,
		)

	if arch_config_handler.args.silent:
		session = operation(None)
	else:
		session = tui.run(lambda: Activity(tr('Installing Arch Linux'), operation, cancellable=False).show())

	if not arch_config_handler.args.silent:
		action: PostInstallationAction = tui.run(
			lambda: select_post_installation(
				session.outcome.elapsed_time,
				str(session.outcome.log_path),
				str(session.outcome.target_mountpoint),
			)
		)

		match action:
			case PostInstallationAction.EXIT:
				pass
			case PostInstallationAction.REBOOT:
				subprocess.run(['reboot'], check=False)
			case PostInstallationAction.CHROOT:
				session.installation.drop_to_shell()

	return session.outcome


def main(arch_config_handler: ArchConfigHandler | None = None) -> None:
	if arch_config_handler is None:
		arch_config_handler = ArchConfigHandler()

	mirror_list_handler = MirrorListHandler(
		offline=arch_config_handler.args.offline,
		verbose=arch_config_handler.args.verbose,
	)

	while True:
		if not arch_config_handler.args.silent:
			show_menu(arch_config_handler, mirror_list_handler)

		arch_config_handler.config.write_debug()
		arch_config_handler.config.save()

		if failure := validate_bootloader_layout(
			arch_config_handler.config.bootloader_config,
			arch_config_handler.config.disk_config,
		):
			error(failure.description)
			if arch_config_handler.args.silent:
				return
			continue

		if arch_config_handler.args.dry_run:
			return

		if not arch_config_handler.args.silent:
			confirmed: bool = tui.run(lambda: confirm_config(arch_config_handler.config))
			if not confirmed:
				debug('Installation aborted')
				continue

		if arch_config_handler.config.disk_config:
			if not delayed_warning(tr('Starting device modifications in ')):
				if arch_config_handler.args.silent:
					return
				continue

		try:
			perform_installation(
				arch_config_handler,
				mirror_list_handler,
				AuthenticationHandler(),
				ApplicationHandler(),
				GamingHandler(),
			)
		except Exception as exception:
			if arch_config_handler.args.silent:
				raise

			debug(''.join(traceback.format_exception(exception)))
			error(f'Installation failed: {exception}')
			message = tr('Installation failed. Review the configuration and try again.') + '\n\n'
			message += '{}: {}'.format(tr('Log file'), logger.path)
			notification = Notify(message)
			_ = tui.run(notification.show)
			continue

		return


if __name__ == '__main__':
	main()
