import secrets
import string
from datetime import UTC, datetime

from archinstall.lib.pathnames import ARCHISO_MOUNTPOINT


def timestamp() -> str:
	now = datetime.now(tz=UTC)
	return now.strftime('%Y-%m-%d %H:%M:%S')


def running_from_iso() -> bool:
	"""
	Check if running from the archiso environment.

	Returns True if /run/archiso/airootfs is a mount point (ISO mode).
	Returns False if running from installed system (host mode) for host-to-target install.
	"""
	return ARCHISO_MOUNTPOINT.is_mount()


def generate_password(length: int = 64) -> str:
	haystack = string.printable  # digits, ascii_letters, punctuation (!"#$[] etc) and whitespace
	return ''.join(secrets.choice(haystack) for _ in range(length))


def format_duration(seconds: float) -> str:
	"""Render a duration as '45s', '2m 38s' or '1h 02m 05s', dropping leading zero units."""
	total = max(0, int(seconds))
	hours, remainder = divmod(total, 3600)
	minutes, secs = divmod(remainder, 60)

	if hours:
		return f'{hours}h {minutes:02d}m {secs:02d}s'
	if minutes:
		return f'{minutes}m {secs:02d}s'
	return f'{secs}s'
