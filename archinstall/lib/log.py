import logging
import os
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from enum import Enum
from pathlib import Path

from archinstall.lib.utils.util import timestamp


class Logger:
	def __init__(self, path: Path | None = None, fallback_path: Path | None = None) -> None:
		self._path = path or Path('/var/log/archinstall')
		self._configured_path = self._path
		self._fallback_path = fallback_path or Path('/tmp') / f'archinstall-{os.getuid()}'
		self._resolved = False
		self._writable = False
		self._initialization_error_reported = False

	@property
	def path(self) -> Path:
		return self._path / 'install.log'

	@path.setter
	def path(self, value: Path) -> None:
		self._path = value
		self._configured_path = value
		self._resolved = False
		self._writable = False
		self._initialization_error_reported = False

	@property
	def directory(self) -> Path:
		return self._path

	def _report_initialization_failure(self, failures: list[tuple[Path, OSError]]) -> None:
		"""Report setup failures without calling back into the logger."""
		if self._initialization_error_reported:
			return

		self._initialization_error_reported = True
		details = '; '.join(f'{path}: {error}' for path, error in failures)
		sys.stderr.write(f'archinstall: unable to initialize file logging ({details}); using stderr\n')

	def _prepare_directory(self, directory: Path, private: bool = False) -> None:
		directory.mkdir(exist_ok=True, parents=True, mode=0o700 if private else 0o755)
		if private:
			metadata = directory.lstat()
			if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
				raise PermissionError(f'Unsafe fallback log directory: {directory}')
			directory.chmod(0o700)

		with (directory / 'install.log').open('a') as file:
			file.write('')

	def _resolve_directory(self) -> bool:
		if self._resolved:
			return self._writable

		self._resolved = True
		failures: list[tuple[Path, OSError]] = []
		fallback = self._fallback_path
		candidates = [(self._configured_path, False)]
		if fallback != self._configured_path:
			candidates.append((fallback, True))

		for directory, private in candidates:
			try:
				self._prepare_directory(directory, private)
			except OSError as exception:
				failures.append((directory, exception))
				continue

			self._path = directory
			self._writable = True
			if failures:
				sys.stderr.write(f'archinstall: logging to fallback directory {directory}\n')
			return True

		self._report_initialization_failure(failures)
		return False

	def log(self, level: int, content: str) -> None:
		if not self._resolve_directory():
			level_name = logging.getLevelName(level)
			sys.stderr.write(f'[{level_name}] {content}\n')
			return

		try:
			with self.path.open('a') as f:
				ts = timestamp()
				level_name = logging.getLevelName(level)
				f.write(f'[{ts}] - {level_name} - {content}\n')
		except OSError as exception:
			# A mount can become read-only after initialization. Reporting this
			# directly avoids the recursive failure mode of the old fallback.
			self._writable = False
			self._report_initialization_failure([(self.path, exception)])
			level_name = logging.getLevelName(level)
			sys.stderr.write(f'[{level_name}] {content}\n')

	def get_content(self, max_bytes: int | None = None) -> bytes:
		content = self.path.read_bytes()

		if max_bytes is not None:
			size = self.path.stat().st_size

			if size > max_bytes:
				content = content[-max_bytes:]

		return content


logger = Logger()


class _LogOutputState:
	def __init__(self) -> None:
		self.tui_active = False
		self.status_sink: Callable[[str], None] | None = None


_log_output_state = _LogOutputState()


def set_tui_logging(active: bool, status_sink: Callable[[str], None] | None = None) -> None:
	_log_output_state.tui_active = active
	_log_output_state.status_sink = status_sink


def tui_logging_active() -> bool:
	"""Return whether Textual currently owns terminal output."""
	return _log_output_state.tui_active


def _safe_status_message(message: str) -> bool:
	lowered = message.lower()
	return not any(secret in lowered for secret in ('password', 'passphrase', 'token', 'secret', 'credential'))


def _supports_color() -> bool:
	"""
	Found first reference here:
		https://stackoverflow.com/questions/7445658/how-to-detect-if-the-console-does-support-ansi-escape-codes-in-python
	And re-used this:
		https://github.com/django/django/blob/master/django/core/management/color.py#L12

	Return True if the running system's terminal supports color,
	and False otherwise.
	"""
	supported_platform = sys.platform != 'win32' or 'ANSICON' in os.environ

	# isatty is not always implemented, #6223.
	is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
	return supported_platform and is_a_tty


class Font(Enum):
	bold = '1'
	italic = '3'
	underscore = '4'
	blink = '5'
	reverse = '7'
	conceal = '8'


def _stylize_output(
	text: str,
	fg: str,
	bg: str | None,
	reset: bool,
	font: list[Font] | None = None,
) -> str:
	"""
	Heavily influenced by:
		https://github.com/django/django/blob/ae8338daf34fd746771e0678081999b656177bae/django/utils/termcolors.py#L13
	Color options here:
		https://askubuntu.com/questions/528928/how-to-do-underline-bold-italic-strikethrough-color-background-and-size-i

	Adds styling to a text given a set of color arguments.
	"""
	colors = {
		'black': '0',
		'red': '1',
		'green': '2',
		'yellow': '3',
		'blue': '4',
		'magenta': '5',
		'cyan': '6',
		'white': '7',
		'teal': '8;5;109',  # Extended 256-bit colors (not always supported)
		'orange': '8;5;208',  # https://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html#256-colors
		'darkorange': '8;5;202',
		'gray': '8;5;246',
		'grey': '8;5;246',
		'darkgray': '8;5;240',
		'lightgray': '8;5;256',
	}

	foreground = {key: f'3{colors[key]}' for key in colors}
	background = {key: f'4{colors[key]}' for key in colors}
	code_list = []

	if text == '' and reset:
		return '\x1b[0m'

	code_list.append(foreground[str(fg)])

	if bg:
		code_list.append(background[str(bg)])

	if font is not None:
		for o in font:
			code_list.append(o.value)

	ansi = ';'.join(code_list)

	return f'\033[{ansi}m{text}\033[0m'


def journal_log(message: str, level: int = logging.DEBUG) -> None:
	try:
		import systemd.journal  # type: ignore[import-not-found]
	except ModuleNotFoundError:
		return

	log_adapter = logging.getLogger('archinstall')
	log_fmt = logging.Formatter('[%(levelname)s]: %(message)s')
	log_ch = systemd.journal.JournalHandler()
	log_ch.setFormatter(log_fmt)
	log_adapter.addHandler(log_ch)
	log_adapter.setLevel(logging.DEBUG)

	log_adapter.log(level, message)


def info(
	*msgs: str,
	level: int = logging.INFO,
	fg: str = 'white',
	bg: str | None = None,
	reset: bool = False,
	font: list[Font] | None = None,
) -> None:
	log(*msgs, level=level, fg=fg, bg=bg, reset=reset, font=font)


def debug(
	*msgs: str,
	level: int = logging.DEBUG,
	fg: str = 'white',
	bg: str | None = None,
	reset: bool = False,
	font: list[Font] | None = None,
) -> None:
	log(*msgs, level=level, fg=fg, bg=bg, reset=reset, font=font)


def error(
	*msgs: str,
	level: int = logging.ERROR,
	fg: str = 'red',
	bg: str | None = None,
	reset: bool = False,
	font: list[Font] | None = None,
) -> None:
	log(*msgs, level=level, fg=fg, bg=bg, reset=reset, font=font)


def warn(
	*msgs: str,
	level: int = logging.WARNING,
	fg: str = 'yellow',
	bg: str | None = None,
	reset: bool = False,
	font: list[Font] | None = None,
) -> None:
	log(*msgs, level=level, fg=fg, bg=bg, reset=reset, font=font)


def log(
	*msgs: str,
	level: int = logging.INFO,
	fg: str = 'white',
	bg: str | None = None,
	reset: bool = False,
	font: list[Font] | None = None,
) -> None:
	text = ' '.join(str(x) for x in msgs)

	logger.log(level, text)

	# Attempt to colorize the output if supported
	# Insert default colors and override with **kwargs
	if _supports_color():
		text = _stylize_output(text, fg, bg, reset, font)

	journal_log(text, level=level)

	sink = _log_output_state.status_sink
	if level != logging.DEBUG and sink is not None and _safe_status_message(text):
		sink(text)

	if level != logging.DEBUG and not _log_output_state.tui_active:
		print(text)


def share_install_log(
	paste_url: str,
	max_bytes: int | None = None,
) -> str | None:
	if urllib.parse.urlparse(paste_url).scheme not in {'http', 'https'}:
		info(f'Unsupported log upload URL: {paste_url}')
		return None

	log_path = logger.path

	if not log_path.exists():
		info(f'Log file not found: {log_path}')
		return None

	content = logger.get_content(max_bytes=max_bytes)

	if len(content) == 0:
		info(f'Log file is empty: {log_path}')
		return None

	try:
		req = urllib.request.Request(paste_url, data=content)
		# The URL scheme is restricted to HTTP(S) above.
		with urllib.request.urlopen(req) as response:  # nosec B310
			url = response.read().decode().strip()
	except urllib.error.URLError as e:
		info(f'Upload failed: {e}')
		return None

	if not url.startswith('http'):
		info(f'Unexpected response from {paste_url}: {url[:200]!r}')
		return None

	return url
