import errno
import logging
import sys
from pathlib import Path
from types import ModuleType

import pytest

import archinstall.lib.log as log_module
from archinstall.lib.command import SysCommand
from archinstall.lib.log import Logger, set_tui_logging


def test_logger_uses_configured_writable_directory(tmp_path: Path) -> None:
	configured = tmp_path / 'configured'
	logger = Logger(configured, tmp_path / 'fallback')
	logger.log(logging.INFO, 'hello')

	assert logger.directory == configured
	assert 'hello' in logger.path.read_text()


@pytest.mark.parametrize('error_number', [errno.EACCES, errno.EROFS])
def test_logger_falls_back_for_os_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error_number: int) -> None:
	configured = tmp_path / 'configured'
	fallback = tmp_path / 'fallback'
	logger = Logger(configured, fallback)
	original = logger._prepare_directory

	def prepare(directory: Path, private: bool = False) -> None:
		if directory == configured:
			raise OSError(error_number, 'unwritable')
		original(directory, private)

	monkeypatch.setattr(logger, '_prepare_directory', prepare)
	logger.log(logging.WARNING, 'fallback message')

	assert logger.directory == fallback
	assert fallback.stat().st_mode & 0o777 == 0o700
	assert 'fallback message' in logger.path.read_text()


def test_logger_creates_missing_path(tmp_path: Path) -> None:
	configured = tmp_path / 'missing' / 'nested'
	logger = Logger(configured, tmp_path / 'fallback')
	logger.log(logging.INFO, 'created')
	assert configured.is_dir()


def test_logger_reports_to_stderr_when_fallback_fails(
	tmp_path: Path,
	monkeypatch: pytest.MonkeyPatch,
	capsys: pytest.CaptureFixture[str],
) -> None:
	logger = Logger(tmp_path / 'configured', tmp_path / 'fallback')

	def fail(directory: Path, private: bool = False) -> None:
		raise OSError(errno.EROFS, 'read-only')

	monkeypatch.setattr(logger, '_prepare_directory', fail)
	logger.log(logging.ERROR, 'still visible')
	logger.log(logging.ERROR, 'second message')
	output = capsys.readouterr().err

	assert output.count('unable to initialize file logging') == 1
	assert 'still visible' in output
	assert 'second message' in output


def test_logger_zero_byte_limit_returns_no_content(tmp_path: Path) -> None:
	logger = Logger(tmp_path / 'logs', tmp_path / 'fallback')
	logger.log(logging.INFO, 'sensitive content')

	assert logger.get_content(max_bytes=0) == b''


def test_logger_rejects_negative_byte_limit(tmp_path: Path) -> None:
	logger = Logger(tmp_path / 'logs', tmp_path / 'fallback')
	logger.log(logging.INFO, 'content')

	with pytest.raises(ValueError, match='non-negative'):
		logger.get_content(max_bytes=-1)


def test_journal_log_reuses_single_handler(monkeypatch: pytest.MonkeyPatch) -> None:
	emitted: list[str] = []

	class FakeJournalHandler(logging.Handler):
		def emit(self, record: logging.LogRecord) -> None:
			emitted.append(record.getMessage())

	journal_module = ModuleType('systemd.journal')
	setattr(journal_module, 'JournalHandler', FakeJournalHandler)
	systemd_module = ModuleType('systemd')
	setattr(systemd_module, 'journal', journal_module)
	monkeypatch.setitem(sys.modules, 'systemd', systemd_module)
	monkeypatch.setitem(sys.modules, 'systemd.journal', journal_module)
	monkeypatch.setattr(log_module, '_journal_handler', None)

	adapter = logging.getLogger('archinstall')
	original_handlers = list(adapter.handlers)
	adapter.handlers.clear()
	try:
		log_module.journal_log('first')
		log_module.journal_log('second')

		assert len(adapter.handlers) == 1
		assert emitted == ['first', 'second']
	finally:
		adapter.handlers[:] = original_handlers


def test_command_peek_output_is_suppressed_while_tui_owns_terminal() -> None:
	set_tui_logging(True)
	try:
		command = SysCommand(['/bin/true'], peek_output=True)
		assert command.peek_output is False
	finally:
		set_tui_logging(False)
