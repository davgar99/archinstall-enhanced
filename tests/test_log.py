import errno
import logging
from pathlib import Path

import pytest

from archinstall.lib.log import Logger


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
