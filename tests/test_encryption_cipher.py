from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pytest import MonkeyPatch

from archinstall.lib.disk import device_handler as device_handler_module
from archinstall.lib.disk import encryption_cipher, encryption_menu, luks
from archinstall.lib.disk.device_handler import DeviceHandler
from archinstall.lib.disk.luks import Luks2
from archinstall.lib.models.device import DiskEncryption, EncryptionType
from archinstall.lib.models.users import Password


def test_chacha_authenticated_mode_is_not_silently_enabled() -> None:
	error = encryption_cipher.validate_luks_cipher('chacha20-random')
	assert error is not None
	assert 'experimental' in error.lower()


def test_supported_cipher_is_benchmarked(monkeypatch: MonkeyPatch) -> None:
	commands: list[list[str]] = []

	def record_command(command: list[str]) -> None:
		commands.append(command)

	monkeypatch.setattr(encryption_cipher, 'SysCommand', record_command)
	assert encryption_cipher.validate_luks_cipher('aes-xts-plain64') is None
	assert commands == [['cryptsetup', 'benchmark', '--cipher', 'aes-xts-plain64', '--key-size', '512']]


def test_non_xts_custom_cipher_is_not_falsely_rejected(monkeypatch: MonkeyPatch) -> None:
	commands: list[list[str]] = []

	monkeypatch.setattr(encryption_cipher, 'SysCommand', commands.append)
	assert encryption_cipher.validate_luks_cipher('aes-cbc-essiv:sha256') is None
	assert commands == [['cryptsetup', 'benchmark', '--cipher', 'aes-cbc-essiv:sha256', '--key-size', '256']]


def test_luks_key_size_doubles_only_for_xts_mode() -> None:
	assert encryption_cipher.luks_key_size(None) == 512
	assert encryption_cipher.luks_key_size('aes-xts-plain64') == 512
	assert encryption_cipher.luks_key_size('serpent-xts-plain64') == 512
	assert encryption_cipher.luks_key_size('aes-cbc-essiv:sha256') == 256
	assert encryption_cipher.luks_key_size('serpent-cbc-essiv:sha256') == 256


def test_luks_cipher_menu_marks_saved_selection_as_default() -> None:
	assert encryption_menu._luks_cipher_default(None) == encryption_cipher.LuksCipher.DEFAULT
	assert encryption_menu._luks_cipher_default('aes-xts-plain64') == encryption_cipher.LuksCipher.AES_XTS
	assert encryption_menu._luks_cipher_default('serpent-xts-plain64') == encryption_cipher.LuksCipher.SERPENT_XTS
	assert encryption_menu._luks_cipher_default('twofish-xts-plain64') == encryption_cipher.LuksCipher.TWOFISH_XTS
	assert encryption_menu._luks_cipher_default('camellia-xts-plain64') == encryption_cipher.LuksCipher.CUSTOM


def test_selected_cipher_reaches_luks_format(monkeypatch: MonkeyPatch) -> None:
	captured: list[list[str]] = []

	def fake_run(command: list[str], input_data: bytes | None = None) -> SimpleNamespace:
		captured.append(command)
		return SimpleNamespace(stdout=b'')

	monkeypatch.setattr(luks, 'run', fake_run)
	handler = Luks2(
		Path('/dev/test'),
		password=Password(plaintext='secret'),
		cipher='serpent-xts-plain64',
	)
	handler.encrypt()

	command = captured[0]
	cipher_index = command.index('--cipher')
	assert command[cipher_index + 1] == 'serpent-xts-plain64'


def test_device_handler_encrypt_forwards_selected_cipher_and_key_size(monkeypatch: MonkeyPatch) -> None:
	captured: dict[str, Any] = {}

	class FakeLuks2:
		def __init__(self, dev_path: Path, mapper_name: str | None = None, password: Password | None = None, cipher: str | None = None) -> None:
			captured['cipher'] = cipher
			self.mapper_dev = Path('/dev/mapper/test')

		def encrypt(self, iter_time: int = 0, key_size: int = 0) -> None:
			captured['key_size'] = key_size

		def unlock(self, key_file: Any = None) -> None:
			return None

		def lock(self) -> None:
			return None

	monkeypatch.setattr(device_handler_module, 'Luks2', FakeLuks2)
	monkeypatch.setattr(device_handler_module, 'udev_sync', lambda: None)

	handler: DeviceHandler = object.__new__(DeviceHandler)
	handler.encrypt(
		Path('/dev/test'),
		'cryptroot',
		Password(plaintext='secret'),
		cipher='serpent-cbc-essiv:sha256',
	)

	assert captured['cipher'] == 'serpent-cbc-essiv:sha256'
	assert captured['key_size'] == 256


def test_device_handler_format_encrypted_forwards_selected_cipher(monkeypatch: MonkeyPatch) -> None:
	captured: dict[str, Any] = {}

	class FakeLuks2:
		def __init__(self, dev_path: Path, mapper_name: str | None = None, password: Password | None = None, cipher: str | None = None) -> None:
			captured['cipher'] = cipher
			self.mapper_dev = Path('/dev/mapper/test')

		def encrypt(self, iter_time: int = 0, key_size: int = 0) -> None:
			captured['key_size'] = key_size

		def unlock(self, key_file: Any = None) -> None:
			return None

		def lock(self) -> None:
			return None

	monkeypatch.setattr(device_handler_module, 'Luks2', FakeLuks2)
	monkeypatch.setattr(device_handler_module, 'udev_sync', lambda: None)
	monkeypatch.setattr(DeviceHandler, 'format', lambda self, fs_type, path: None)

	enc_conf = DiskEncryption(
		encryption_type=EncryptionType.LUKS,
		encryption_password=Password(plaintext='secret'),
		partitions=[SimpleNamespace(obj_id='root')],  # type: ignore[list-item]
		cipher='serpent-xts-plain64',
	)

	handler: DeviceHandler = object.__new__(DeviceHandler)
	handler.format_encrypted(Path('/dev/test'), 'cryptroot', SimpleNamespace(), enc_conf)  # type: ignore[arg-type]

	assert captured['cipher'] == 'serpent-xts-plain64'
	assert captured['key_size'] == 512


def test_cipher_survives_disk_encryption_config_round_trip() -> None:
	partition: Any = SimpleNamespace(obj_id='root')
	disk_config: Any = SimpleNamespace(
		device_modifications=[SimpleNamespace(partitions=[partition])],
		lvm_config=None,
	)
	password = Password(plaintext='secret')
	original = DiskEncryption(
		encryption_type=EncryptionType.LUKS,
		encryption_password=password,
		partitions=[partition],
		cipher='twofish-xts-plain64',
	)

	serialized = original.json()
	assert serialized['cipher'] == 'twofish-xts-plain64'

	restored = DiskEncryption.parse_arg(disk_config, serialized, password)
	assert restored is not None
	assert restored.cipher == 'twofish-xts-plain64'
