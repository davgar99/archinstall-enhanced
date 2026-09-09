from pathlib import Path
from typing import override

from archinstall.lib.disk.encryption_cipher import LuksCipher, validate_luks_cipher
from archinstall.lib.disk.fido import Fido2
from archinstall.lib.menu.abstract_menu import AbstractSubMenu
from archinstall.lib.menu.helpers import Input, Notify, Selection, Table
from archinstall.lib.menu.menu_helper import MenuHelper
from archinstall.lib.menu.util import get_password
from archinstall.lib.models.device import (
	DEFAULT_ITER_TIME,
	DeviceModification,
	DiskEncryption,
	EncryptionType,
	Fido2Device,
	LvmConfiguration,
	LvmVolume,
	PartitionModification,
)
from archinstall.lib.models.users import Password
from archinstall.lib.translationhandler import tr
from archinstall.lib.utils.format import as_table
from archinstall.tui.menu_item import MenuItem, MenuItemGroup
from archinstall.tui.result import ResultType


class DiskEncryptionMenu(AbstractSubMenu[DiskEncryption]):
	def __init__(
		self,
		device_modifications: list[DeviceModification],
		lvm_config: LvmConfiguration | None = None,
		preset: DiskEncryption | None = None,
	):
		self._enc_config = preset or DiskEncryption()
		self._device_modifications = device_modifications
		self._lvm_config = lvm_config

		menu_options = self._define_menu_options()
		self._item_group = MenuItemGroup(menu_options, sort_items=False, checkmarks=True)
		super().__init__(self._item_group, self._enc_config, allow_reset=True)

	def _define_menu_options(self) -> list[MenuItem]:
		return [
			MenuItem(
				text=tr('Encryption type'),
				action=lambda x: select_encryption_type(self._lvm_config, x),
				value=self._enc_config.encryption_type,
				preview_action=self._prev_type,
				key='encryption_type',
			),
			MenuItem(
				text=tr('Encryption password'),
				action=lambda x: select_encrypted_password(),
				value=self._enc_config.encryption_password,
				dependencies=[self._check_dep_enc_type],
				preview_action=self._prev_password,
				key='encryption_password',
			),
			MenuItem(
				text=tr('Iteration time'),
				action=select_iteration_time,
				value=self._enc_config.iter_time,
				dependencies=[self._check_dep_enc_type],
				preview_action=self._prev_iter_time,
				key='iter_time',
			),
			MenuItem(
				text=tr('LUKS cipher'),
				action=select_luks_cipher,
				value=self._enc_config.cipher,
				dependencies=[self._check_dep_enc_type],
				preview_action=self._prev_cipher,
				key='cipher',
			),
			MenuItem(
				text=tr('Partitions'),
				action=lambda x: select_partitions_to_encrypt(self._device_modifications, x),
				value=self._enc_config.partitions,
				dependencies=[self._check_dep_partitions],
				preview_action=self._prev_partitions,
				key='partitions',
			),
			MenuItem(
				text=tr('LVM volumes'),
				action=self._select_lvm_vols,
				value=self._enc_config.lvm_volumes,
				dependencies=[self._check_dep_lvm_vols],
				preview_action=self._prev_lvm_vols,
				key='lvm_volumes',
			),
			MenuItem(
				text=tr('HSM'),
				action=select_hsm,
				value=self._enc_config.hsm_device,
				dependencies=[self._check_dep_enc_type],
				preview_action=self._prev_hsm,
				key='hsm_device',
			),
		]

	async def _select_lvm_vols(self, preset: list[LvmVolume]) -> list[LvmVolume]:
		if self._lvm_config:
			return await select_lvm_vols_to_encrypt(self._lvm_config, preset=preset)
		return []

	def _check_dep_enc_type(self) -> bool:
		enc_type: EncryptionType | None = self._item_group.find_by_key('encryption_type').value
		return bool(enc_type and enc_type != EncryptionType.NO_ENCRYPTION)

	def _check_dep_partitions(self) -> bool:
		enc_type: EncryptionType | None = self._item_group.find_by_key('encryption_type').value
		return bool(enc_type and enc_type in [EncryptionType.LUKS, EncryptionType.LVM_ON_LUKS])

	def _check_dep_lvm_vols(self) -> bool:
		enc_type: EncryptionType | None = self._item_group.find_by_key('encryption_type').value
		return bool(enc_type and enc_type == EncryptionType.LUKS_ON_LVM)

	@override
	async def show(self) -> DiskEncryption | None:
		enc_config = await super().show()
		if enc_config is None:
			return None

		enc_type: EncryptionType | None = self._item_group.find_by_key('encryption_type').value
		enc_password: Password | None = self._item_group.find_by_key('encryption_password').value
		iter_time: int | None = self._item_group.find_by_key('iter_time').value
		cipher: str | None = self._item_group.find_by_key('cipher').value
		enc_partitions = self._item_group.find_by_key('partitions').value
		enc_lvm_vols = self._item_group.find_by_key('lvm_volumes').value

		assert enc_type is not None
		assert enc_partitions is not None
		assert enc_lvm_vols is not None

		if enc_type in [EncryptionType.LUKS, EncryptionType.LVM_ON_LUKS] and enc_partitions:
			enc_lvm_vols = []
		if enc_type == EncryptionType.LUKS_ON_LVM:
			enc_partitions = []

		if enc_type != EncryptionType.NO_ENCRYPTION and enc_password and (enc_partitions or enc_lvm_vols):
			result = DiskEncryption(
				encryption_password=enc_password,
				encryption_type=enc_type,
				partitions=enc_partitions,
				lvm_volumes=enc_lvm_vols,
				hsm_device=enc_config.hsm_device,
				iter_time=iter_time or DEFAULT_ITER_TIME,
				cipher=cipher,
			)
			return result

		return None

	def _prev_type(self, item: MenuItem) -> str | None:
		enc_type = self._item_group.find_by_key('encryption_type').value
		if enc_type:
			return f'{tr("Encryption type")}: {enc_type.type_to_text()}'
		return None

	def _prev_password(self, item: MenuItem) -> str | None:
		if item.value:
			return f'{tr("Encryption password")}: {item.value.hidden()}'
		return None

	def _prev_cipher(self, item: MenuItem) -> str | None:
		cipher = item.value or tr('Cryptsetup default')
		return f'{tr("LUKS cipher")}: {cipher}'

	def _prev_partitions(self, item: MenuItem) -> str | None:
		if item.value:
			return (tr('Partitions to be encrypted') + '\n' + as_table(item.value)).rstrip()
		return None

	def _prev_lvm_vols(self, item: MenuItem) -> str | None:
		if item.value:
			return (tr('LVM volumes to be encrypted') + '\n' + as_table(item.value)).rstrip()
		return None

	def _prev_hsm(self, item: MenuItem) -> str | None:
		if not item.value:
			return None
		fido_device: Fido2Device = item.value
		output = f'{fido_device.path} ({fido_device.manufacturer}, {fido_device.product})'
		return f'{tr("HSM device")}: {output}'

	def _prev_iter_time(self, item: MenuItem) -> str | None:
		if item.value:
			iter_time = item.value
			enc_type = self._item_group.find_by_key('encryption_type').value
			if iter_time and enc_type != EncryptionType.NO_ENCRYPTION:
				return f'{tr("Iteration time")}: {iter_time}ms'
		return None


async def select_luks_cipher(preset: str | None = None) -> str | None:
	items = [MenuItem(cipher.display_msg(), value=cipher) for cipher in LuksCipher]
	group = MenuItemGroup(items, sort_items=False)
	group.set_default_by_value(LuksCipher.DEFAULT)
	result = await Selection[LuksCipher](
		group,
		header=tr('Select a LUKS2 cipher. The cryptsetup default is recommended unless you have a specific requirement.'),
		allow_skip=True,
		allow_reset=True,
	).show()

	choice = LuksCipher.DEFAULT
	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Reset:
			return None
		case ResultType.Selection:
			choice = result.get_value()

	if choice == LuksCipher.DEFAULT:
		return None

	if choice == LuksCipher.CUSTOM:
		custom = await Input(
			header=tr('Enter a cryptsetup cipher specification (for example aes-xts-plain64).'),
			allow_skip=True,
			default_value=preset or '',
			validator_callback=lambda value: validate_luks_cipher(value or ''),
		).show()
		if custom.type_ == ResultType.Skip:
			return preset
		if custom.type_ != ResultType.Selection or not custom.get_value():
			return preset
		candidate = custom.get_value()
	else:
		candidate = choice.value

	if error := validate_luks_cipher(candidate):
		await Notify(error).show()
		return preset
	return candidate


async def select_encryption_type(
	lvm_config: LvmConfiguration | None = None,
	preset: EncryptionType | None = None,
) -> EncryptionType | None:
	options = [EncryptionType.LVM_ON_LUKS, EncryptionType.LUKS_ON_LVM] if lvm_config else [EncryptionType.LUKS]
	if not preset:
		preset = options[0]

	items = [MenuItem(option.type_to_text(), value=option) for option in options]
	group = MenuItemGroup(items)
	result = await Selection[EncryptionType](
		group,
		header=tr('Select encryption type'),
		allow_skip=True,
		allow_reset=True,
	).show()
	match result.type_:
		case ResultType.Reset:
			return None
		case ResultType.Skip:
			return preset
		case ResultType.Selection:
			return result.get_value()


async def select_encrypted_password() -> Password | None:
	return await get_password(header=tr('Enter disk encryption password (leave blank for no encryption)') + '\n', allow_skip=True)


async def select_hsm(preset: Fido2Device | None = None) -> Fido2Device | None:
	header = tr('Select a FIDO2 device to use for HSM') + '\n'
	try:
		fido_devices = Fido2.get_cryptenroll_devices()
	except ValueError:
		return None

	if fido_devices:
		group = MenuHelper(data=fido_devices).create_menu_group()
		result = await Selection[Fido2Device](group, header=header, allow_skip=True).show()
		match result.type_:
			case ResultType.Reset:
				return None
			case ResultType.Skip:
				return preset
			case ResultType.Selection:
				return result.get_value()
	return None


async def select_partitions_to_encrypt(
	modification: list[DeviceModification],
	preset: list[PartitionModification],
) -> list[PartitionModification]:
	partitions: list[PartitionModification] = []
	for mod in modification:
		partitions += [partition for partition in mod.partitions if partition.mountpoint != Path('/boot')]

	avail_partitions = [partition for partition in partitions if not partition.exists()]
	if avail_partitions:
		group = MenuItemGroup.from_objects(avail_partitions)
		group.set_selected_by_value(preset)
		result = await Table[PartitionModification](
			header=tr('Select disks for the installation'),
			group=group,
			allow_skip=True,
			multi=True,
		).show()
		match result.type_:
			case ResultType.Reset:
				return []
			case ResultType.Skip:
				return preset
			case ResultType.Selection:
				return result.get_values()
	return []


async def select_lvm_vols_to_encrypt(lvm_config: LvmConfiguration, preset: list[LvmVolume]) -> list[LvmVolume]:
	volumes = lvm_config.get_all_volumes()
	if volumes:
		group = MenuItemGroup.from_objects(volumes)
		group.set_selected_by_value(preset)
		result = await Table[LvmVolume](
			header=tr('Select disks for the installation'),
			group=group,
			allow_skip=True,
			multi=True,
		).show()
		match result.type_:
			case ResultType.Reset:
				return []
			case ResultType.Skip:
				return preset
			case ResultType.Selection:
				return result.get_values()
	return []


async def select_iteration_time(preset: int | None = None) -> int | None:
	header = tr('Enter iteration time for LUKS encryption (in milliseconds)') + '\n'
	header += tr('Higher values increase security but slow down boot time') + '\n'
	header += tr('Default: {}ms, Recommended range: 1000-60000').format(DEFAULT_ITER_TIME) + '\n'

	def validate_iter_time(value: str) -> str | None:
		try:
			iter_time = int(value)
			if iter_time < 100:
				return tr('Iteration time must be at least 100ms')
			if iter_time > 120000:
				return tr('Iteration time must be at most 120000ms')
			return None
		except ValueError:
			return tr('Please enter a valid number')

	result = await Input(
		header=header,
		allow_skip=True,
		default_value=str(preset) if preset else str(DEFAULT_ITER_TIME),
		validator_callback=validate_iter_time,
	).show()
	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Selection:
			if not result.get_value():
				return preset
			return int(result.get_value())
		case ResultType.Reset:
			return None
