import readline

from archinstall.lib.args import USER_CONFIG_FILE, USER_CREDS_FILE, ArchConfig
from archinstall.lib.log import debug
from archinstall.lib.menu.helpers import Confirmation, Selection
from archinstall.lib.menu.util import get_password, prompt_dir
from archinstall.lib.models.device import ModificationStatus
from archinstall.lib.translationhandler import tr
from archinstall.tui.menu_item import MenuItem, MenuItemGroup
from archinstall.tui.result import ResultType


async def confirm_config(config: ArchConfig) -> bool:
	header = f'{tr("The specified configuration will be applied")}. '
	header += tr('Continue to the final confirmation?') + '\n'

	group = MenuItemGroup.yes_no()
	group.set_preview_for_all(lambda _item: config.as_summary())

	result = await Confirmation(
		group=group,
		header=header,
		allow_skip=False,
		preset=False,
		preview_location='bottom',
		preview_header=tr('Configuration preview'),
	).show()

	if not result.get_value():
		return False

	destructive_targets = _destructive_targets(config)
	if destructive_targets:
		warning = tr('WARNING: DATA WILL BE PERMANENTLY DELETED') + '\n\n'
		warning += tr('The following drives contain destructive changes:') + '\n'
		warning += '\n'.join(f'- {target}' for target in destructive_targets) + '\n\n'
		warning += tr('This cannot be undone. Erase the listed data and install?') + '\n'
		result = await Confirmation(
			header=warning,
			allow_skip=False,
			preset=False,
		).show()
		if not result.get_value():
			return False

	return True


def _destructive_targets(config: ArchConfig) -> list[str]:
	if config.disk_config is None:
		return []

	targets: list[str] = []
	for modification in config.disk_config.device_modifications:
		partition_data_loss = any(partition.status in {ModificationStatus.MODIFY, ModificationStatus.DELETE} for partition in modification.partitions)
		if not modification.wipe and not partition_data_loss:
			continue

		info = modification.device.device_info
		size = info.total_size.format_highest()
		scope = tr('entire drive') if modification.wipe else tr('selected partitions')
		targets.append(f'{info.path} — {info.model} — {size} ({scope})')

	return targets


async def save_config(config: ArchConfig) -> None:
	def preview(item: MenuItem) -> str | None:
		match item.value:
			case 'user_config':
				serialized = config.user_config_to_json()
				return f'{USER_CONFIG_FILE}\n{serialized}'
			case 'user_creds':
				if maybe_serial := config.user_credentials_to_json():
					return f'{USER_CREDS_FILE}\n{maybe_serial}'
				return tr('No configuration')
			case 'all':
				output = [str(USER_CONFIG_FILE)]
				config.user_credentials_to_json()
				output.append(str(USER_CREDS_FILE))
				return '\n'.join(output)
		return None

	items = [
		MenuItem(
			tr('Save user configuration (including disk layout)'),
			value='user_config',
			preview_action=preview,
		),
		MenuItem(
			tr('Save user credentials'),
			value='user_creds',
			preview_action=preview,
		),
		MenuItem(
			tr('Save all'),
			value='all',
			preview_action=preview,
		),
	]

	group = MenuItemGroup(items)
	result = await Selection[str](
		group,
		allow_skip=True,
		preview_location='right',
	).show()

	match result.type_:
		case ResultType.Skip:
			return
		case ResultType.Selection:
			save_option = result.get_value()
		case _:
			raise ValueError('Unhandled return type')

	readline.set_completer_delims('\t\n=')
	readline.parse_and_bind('tab: complete')

	dest_path = await prompt_dir(
		tr('Enter a directory for the configuration(s) to be saved') + '\n',
		allow_skip=True,
	)

	if not dest_path:
		return

	header = tr('Do you want to save the configuration file(s) to {}?').format(dest_path)

	save_result = await Confirmation(
		header=header,
		allow_skip=False,
		preset=True,
	).show()

	match save_result.type_:
		case ResultType.Selection:
			if not save_result.get_value():
				return
		case _:
			return

	debug(f'Saving configuration files to {dest_path.absolute()}')

	header = tr('Do you want to encrypt the user_credentials.json file?')

	enc_result = await Confirmation(
		header=header,
		allow_skip=False,
		preset=False,
	).show()

	enc_password: str | None = None
	if enc_result.type_ == ResultType.Selection:
		if enc_result.get_value():
			password = await get_password(
				header=tr('Credentials file encryption password'),
				allow_skip=True,
			)

			if password:
				enc_password = password.plaintext

	match save_option:
		case 'user_config':
			config.save_user_config(dest_path)
		case 'user_creds':
			config.save_user_creds(dest_path, password=enc_password)
		case 'all':
			config.save(dest_path, creds=True, password=enc_password)
