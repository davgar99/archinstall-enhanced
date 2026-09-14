from pathlib import Path

import pytest
from pytest import MonkeyPatch

import archinstall.lib.profile.profiles_handler as profiles_handler_module
from archinstall.default_profiles.profile import Profile, ProfileType
from archinstall.lib.profile.profiles_handler import ProfileHandler


def test_remote_profile_config_registers_profile_and_removes_temp_file(monkeypatch: MonkeyPatch) -> None:
	handler = ProfileHandler()
	remote_profile = Profile('Remote Test', ProfileType.Custom)
	temporary_paths: list[Path] = []

	def no_default_profiles() -> list[Profile]:
		return []

	def fetch_profile(url: str) -> bytes:
		assert url == 'https://example.invalid/profile.py'
		return b'remote profile data'

	def process_profile(file: Path) -> list[Profile]:
		temporary_paths.append(file)
		assert file.is_file()
		assert file.read_bytes() == b'remote profile data'
		return [remote_profile]

	monkeypatch.setattr(handler, '_find_available_profiles', no_default_profiles)
	monkeypatch.setattr(handler, '_process_profile_file', process_profile)
	monkeypatch.setattr(profiles_handler_module, 'fetch_data_from_url', fetch_profile)

	loaded = handler.parse_profile_config(
		{
			'path': 'https://example.invalid/profile.py',
			'main': 'Remote Test',
		}
	)

	assert loaded is remote_profile
	assert handler.get_profile_by_name('Remote Test') is remote_profile
	assert len(temporary_paths) == 1
	assert not temporary_paths[0].exists()


def test_remote_profile_temp_file_is_removed_when_processing_fails(monkeypatch: MonkeyPatch) -> None:
	handler = ProfileHandler()
	temporary_paths: list[Path] = []

	def fetch_profile(url: str) -> bytes:
		return b'invalid profile data'

	def fail_processing(file: Path) -> list[Profile]:
		temporary_paths.append(file)
		raise RuntimeError('profile processing failed')

	monkeypatch.setattr(handler, '_process_profile_file', fail_processing)
	monkeypatch.setattr(profiles_handler_module, 'fetch_data_from_url', fetch_profile)

	with pytest.raises(RuntimeError, match='profile processing failed'):
		handler._import_profile_from_url('https://example.invalid/broken.py')

	assert len(temporary_paths) == 1
	assert not temporary_paths[0].exists()
