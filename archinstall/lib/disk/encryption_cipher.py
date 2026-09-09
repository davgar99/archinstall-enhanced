import re
from enum import StrEnum

from archinstall.lib.command import SysCommand
from archinstall.lib.exceptions import SysCallError


class LuksCipher(StrEnum):
	DEFAULT = 'default'
	AES_XTS = 'aes-xts-plain64'
	SERPENT_XTS = 'serpent-xts-plain64'
	TWOFISH_XTS = 'twofish-xts-plain64'
	CUSTOM = 'custom'

	def display_msg(self) -> str:
		return {
			LuksCipher.DEFAULT: 'Cryptsetup default (recommended)',
			LuksCipher.AES_XTS: 'AES-XTS (aes-xts-plain64)',
			LuksCipher.SERPENT_XTS: 'Serpent-XTS (serpent-xts-plain64)',
			LuksCipher.TWOFISH_XTS: 'Twofish-XTS (twofish-xts-plain64)',
			LuksCipher.CUSTOM: 'Custom cipher (advanced)',
		}[self]


_CIPHER_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9:+_.-]{0,127}$')


def normalize_luks_cipher(cipher: str | None) -> str | None:
	if not cipher or cipher == LuksCipher.DEFAULT:
		return None
	return cipher


def validate_luks_cipher(cipher: str) -> str | None:
	"""Return an error message for unsupported or unsafe-to-autoconfigure ciphers."""
	if not _CIPHER_PATTERN.fullmatch(cipher):
		return 'Cipher names may contain only letters, numbers, colon, plus, underscore, dot, and hyphen.'

	lower = cipher.lower()
	if 'chacha20' in lower or 'poly1305' in lower:
		return (
			'Authenticated ChaCha20/Poly1305 disk encryption currently requires the experimental '
			'dm-integrity path and cannot be enabled by this standard LUKS2 cipher selector.'
		)

	try:
		SysCommand(['cryptsetup', 'benchmark', '--cipher', cipher, '--key-size', '512'])
	except SysCallError as err:
		return f'Cryptsetup could not use cipher {cipher}: {err}'
	return None
