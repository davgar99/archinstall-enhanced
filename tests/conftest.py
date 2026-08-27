from collections.abc import Iterator
from pathlib import Path

import pytest

from archinstall.lib.log import logger


@pytest.fixture(autouse=True)
def temporary_log_directory(tmp_path: Path) -> Iterator[None]:
	"""Keep tests independent of the host's /var/log permissions."""
	previous_path = logger.directory
	logger.path = tmp_path / 'archinstall-log'
	try:
		yield
	finally:
		logger.path = previous_path


@pytest.fixture(scope='session')
def config_fixture() -> Path:
	return Path(__file__).parent / 'data' / 'test_config.json'


@pytest.fixture(scope='session')
def example_config_fixture() -> Path:
	return Path(__file__).parent.parent / 'examples' / 'config-sample.json'


@pytest.fixture(scope='session')
def example_creds_fixture() -> Path:
	return Path(__file__).parent.parent / 'examples' / 'creds-sample.json'


@pytest.fixture(scope='session')
def btrfs_config_fixture() -> Path:
	return Path(__file__).parent / 'data' / 'test_config_btrfs.json'


@pytest.fixture(scope='session')
def creds_fixture() -> Path:
	return Path(__file__).parent / 'data' / 'test_creds.json'


@pytest.fixture(scope='session')
def encrypted_creds_fixture() -> Path:
	return Path(__file__).parent / 'data' / 'test_encrypted_creds.json'


@pytest.fixture(scope='session')
def deprecated_creds_config() -> Path:
	return Path(__file__).parent / 'data' / 'test_deprecated_creds_config.json'


@pytest.fixture(scope='session')
def deprecated_mirror_config() -> Path:
	return Path(__file__).parent / 'data' / 'test_deprecated_mirror_config.json'


@pytest.fixture(scope='session')
def deprecated_audio_config() -> Path:
	return Path(__file__).parent / 'data' / 'test_deprecated_audio_config.json'


@pytest.fixture(scope='session')
def mirrorlist_no_country_fixture() -> Path:
	return Path(__file__).parent / 'data' / 'mirrorlists' / 'test_no_country'


@pytest.fixture(scope='session')
def mirrorlist_with_country_fixture() -> Path:
	return Path(__file__).parent / 'data' / 'mirrorlists' / 'test_with_country'


@pytest.fixture(scope='session')
def mirrorlist_multiple_countries_fixture() -> Path:
	return Path(__file__).parent / 'data' / 'mirrorlists' / 'test_multiple_countries'
