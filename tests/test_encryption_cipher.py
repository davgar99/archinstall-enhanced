from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pytest import MonkeyPatch

from archinstall.lib.disk import encryption_cipher, luks
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
