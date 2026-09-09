import shlex
from dataclasses import dataclass
from pathlib import Path
from subprocess import CalledProcessError
from types import TracebackType

from archinstall.lib.command import SysCommand, SysCommandWorker, run
from archinstall.lib.disk.encryption_cipher import normalize_luks_cipher
from archinstall.lib.disk.utils import get_lsblk_info, swapon, umount
from archinstall.lib.exceptions import DiskError, SysCallError
from archinstall.lib.log import debug, info
from archinstall.lib.models.device import DEFAULT_ITER_TIME
from archinstall.lib.models.users import Password
from archinstall.lib.utils.util import generate_password


def ensure_dm_crypt_available() -> None:
	"""Ensure the live environment exposes the device-mapper crypt target before opening LUKS volumes."""
	if Path('/sys/module/dm_crypt').exists():
		return

	try:
		SysCommand('modprobe dm-crypt')
	except SysCallError as err:
		raise DiskError('dm-crypt kernel support is unavailable. The installer cannot unlock LUKS volumes until the dm-crypt module is available.') from err

	if not Path('/sys/module/dm_crypt').exists():
		raise DiskError('dm-crypt was requested but the kernel did not expose the dm-crypt module.')


def activate_swap_mapper_if_needed(mapper_dev: Path) -> bool:
	"""Activate an unlocked mapper when its inner filesystem is swap."""
	try:
		fs_type = SysCommand(['blkid', '-o', 'value', '-s', 'TYPE', str(mapper_dev)]).decode().strip()
	except SysCallError:
		return False

	if fs_type != 'swap':
		return False

	swapon(mapper_dev)
	return True


@dataclass
class Luks2:
	luks_dev_path: Path
	mapper_name: str | None = None
	password: Password | None = None
	key_file: Path | None = None
	auto_unmount: bool = False
	cipher: str | None = None

	@property
	def mapper_dev(self) -> Path | None:
		if self.mapper_name:
			return Path(f'/dev/mapper/{self.mapper_name}')
		return None

	def isLuks(self) -> bool:
		try:
			SysCommand(f'cryptsetup isLuks {self.luks_dev_path}')
			return True
		except SysCallError:
			return False

	def erase(self) -> None:
		debug(f'Erasing luks partition: {self.luks_dev_path}')
		worker = SysCommandWorker(f'cryptsetup erase {self.luks_dev_path}')
		worker.poll()
		worker.write(b'YES\n', line_ending=False)

	def __enter__(self) -> None:
		self.unlock(self.key_file)

	def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None) -> None:
		if self.auto_unmount:
			self.lock()

	def _password_bytes(self) -> bytes:
		if not self.password:
			raise ValueError('Password for luks2 device was not specified')

		if isinstance(self.password, bytes):
			return self.password
		return bytes(self.password.plaintext, 'UTF-8')

	def _get_passphrase_args(self, key_file: Path | None = None) -> tuple[list[str], bytes | None]:
		key_file = key_file or self.key_file
		if key_file:
			return ['--key-file', str(key_file)], None
		return [], self._password_bytes()

	def encrypt(
		self,
		key_size: int = 512,
		hash_type: str = 'sha512',
		iter_time: int = DEFAULT_ITER_TIME,
		key_file: Path | None = None,
	) -> Path | None:
		debug(f'Luks2 encrypting: {self.luks_dev_path}')
		key_file_arg, passphrase = self._get_passphrase_args(key_file)
		cipher = normalize_luks_cipher(self.cipher)
		cipher_args = ['--cipher', cipher] if cipher else []

		cmd = [
			'cryptsetup',
			'--batch-mode',
			'--verbose',
			'--type',
			'luks2',
			'--pbkdf',
			'argon2id',
			'--hash',
			hash_type,
			'--key-size',
			str(key_size),
			'--iter-time',
			str(iter_time),
			*cipher_args,
			*key_file_arg,
			'--use-urandom',
			'luksFormat',
			str(self.luks_dev_path),
		]

		debug(f'cryptsetup format: {shlex.join(cmd)}')
		try:
			result = run(cmd, input_data=passphrase)
		except CalledProcessError as err:
			output = err.stdout.decode().rstrip()
			raise DiskError(f'Could not encrypt volume "{self.luks_dev_path}": {output}')

		debug(f'cryptsetup luksFormat output: {result.stdout.decode().rstrip()}')
		self.key_file = key_file
		return key_file

	def _get_luks_uuid(self) -> str:
		command = f'cryptsetup luksUUID {self.luks_dev_path}'
		try:
			return SysCommand(command).decode()
		except SysCallError as err:
			info(f'Unable to get UUID for Luks device: {self.luks_dev_path}')
			raise err

	def is_unlocked(self) -> bool:
		return (mapper_dev := self.mapper_dev) is not None and mapper_dev.is_symlink()

	def unlock(self, key_file: Path | None = None) -> None:
		debug(f'Unlocking luks2 device: {self.luks_dev_path}')
		if not self.mapper_name:
			raise ValueError('mapper name missing')

		ensure_dm_crypt_available()
		key_file_arg, passphrase = self._get_passphrase_args(key_file)
		cmd = [
			'cryptsetup',
			'open',
			str(self.luks_dev_path),
			str(self.mapper_name),
			*key_file_arg,
			'--type',
			'luks2',
		]

		try:
			result = run(cmd, input_data=passphrase)
		except CalledProcessError as err:
			output = err.stdout.decode().rstrip()
			raise DiskError(f'Could not unlock luks2 device "{self.luks_dev_path}": {output}')

		debug(f'cryptsetup open output: {result.stdout.decode().rstrip()}')
		if not self.is_unlocked():
			raise DiskError(f'Failed to open luks2 device: {self.luks_dev_path}')

	def lock(self) -> None:
		umount(self.luks_dev_path)
		lsblk_info = get_lsblk_info(self.luks_dev_path)

		for child in lsblk_info.children:
			for mountpoint in child.mountpoints:
				debug(f'Unmounting {mountpoint}')
				umount(mountpoint, recursive=True)
			debug(f'Closing crypt device {child.name}')
			SysCommand(f'cryptsetup close {child.name}')

	def create_keyfile(self, target_path: Path, override: bool = False) -> None:
		if self.mapper_name is None:
			raise ValueError('Mapper name must be provided')

		kf_path = Path(f'/etc/cryptsetup-keys.d/{self.mapper_name}.key')
		key_file = target_path / kf_path.relative_to(kf_path.root)
		crypttab_path = target_path / 'etc/crypttab'

		if key_file.exists():
			if not override:
				info(f'Key file {key_file} already exists, keeping existing')
				return
			info(f'Key file {key_file} already exists, overriding')

		key_file.parent.mkdir(parents=True, exist_ok=True)
		pwd = generate_password(length=512)
		key_file.write_text(pwd)
		key_file.chmod(0o400)
		self._add_key(key_file)
		self._crypttab(crypttab_path, kf_path, options=['luks', 'key-slot=1'])

	def create_crypttab_entry(self, target_path: Path) -> None:
		if self.mapper_name is None:
			raise ValueError('Mapper name must be provided')

		crypttab_path = target_path / 'etc/crypttab'
		crypttab_path.parent.mkdir(parents=True, exist_ok=True)
		self._crypttab(crypttab_path, Path('none'), options=['luks'])

	def _add_key(self, key_file: Path) -> None:
		debug(f'Adding additional key-file {key_file}')
		command = f'cryptsetup -q -v luksAddKey {self.luks_dev_path} {key_file}'
		worker = SysCommandWorker(command)
		pw_injected = False

		while worker.is_alive():
			if b'Enter any existing passphrase' in worker and pw_injected is False:
				worker.write(self._password_bytes())
				pw_injected = True

		if worker.exit_code != 0:
			raise DiskError(f'Could not add encryption key {key_file} to {self.luks_dev_path}: {worker.decode()}')

	def _crypttab(self, crypttab_path: Path, key_file: Path, options: list[str]) -> None:
		debug(f'Adding crypttab entry for key {key_file}')
		with open(crypttab_path, 'a') as crypttab:
			opt = ','.join(options)
			uuid = self._get_luks_uuid()
			row = f'{self.mapper_name} UUID={uuid} {key_file} {opt}\n'
			crypttab.write(row)


def unlock_luks2_dev(dev_path: Path, mapper_name: str, enc_password: Password | None) -> Luks2:
	luks_handler = Luks2(dev_path, mapper_name=mapper_name, password=enc_password)
	if not luks_handler.is_unlocked():
		luks_handler.unlock()
	if mapper_dev := luks_handler.mapper_dev:
		activate_swap_mapper_if_needed(mapper_dev)
	return luks_handler
