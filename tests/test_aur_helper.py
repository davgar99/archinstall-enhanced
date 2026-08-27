from pathlib import Path
from typing import Any, cast, override

import pytest

from archinstall.applications.aur_helper import AurHelperApp
from archinstall.lib.applications.application_menu import ApplicationMenu
from archinstall.lib.models.application import ApplicationConfiguration, AurHelper, AurHelperConfiguration
from archinstall.lib.models.users import Password, User


class FakeInstaller:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.packages: list[str] = []
		self.commands: list[tuple[str, str | None, bool]] = []
		self.sudoers_snapshots: list[str] = []

	def add_additional_packages(self, packages: list[str]) -> None:
		self.packages.extend(packages)

	def arch_chroot(self, command: str, run_as: str | None = None, peek_output: bool = False) -> None:
		for sudoers_path in (self.target / 'etc/sudoers.d').glob('99-archinstall-aur-builder-*'):
			self.sudoers_snapshots.append(sudoers_path.read_text())
		self.commands.append((command, run_as, peek_output))


class FailingInstaller(FakeInstaller):
	@override
	def arch_chroot(self, command: str, run_as: str | None = None, peek_output: bool = False) -> None:
		super().arch_chroot(command, run_as, peek_output)
		raise RuntimeError('AUR build failed')


def test_aur_helper_configuration_roundtrip() -> None:
	config = ApplicationConfiguration(aur_helper_config=AurHelperConfiguration(AurHelper.PARU))

	assert config.json()['aur_helper_config'] == {'aur_helper': 'paru'}
	serialized = cast(dict[str, Any], config.json())
	assert ApplicationConfiguration.parse_arg(serialized) == config
	assert 'AUR helper: paru' in config.summary()


def test_aur_helper_menu_is_available() -> None:
	item = ApplicationMenu()._item_group.find_by_key('aur_helper_config')
	assert item.enabled


def test_aur_helper_builds_as_configured_sudo_user(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	users = [
		User('regular', Password(enc_password='test'), sudo=False),
		User('builder', Password(enc_password='test'), sudo=True),
	]

	AurHelperApp().install(installer, AurHelperConfiguration(AurHelper.YAY), users)  # type: ignore[arg-type]

	assert installer.packages == ['base-devel', 'git']
	assert installer.commands == [
		('rm -rf -- /tmp/archinstall-yay', None, False),
		('install -d -m 0700 -o builder -- /tmp/archinstall-yay', None, False),
		('git clone --depth=1 https://aur.archlinux.org/yay.git /tmp/archinstall-yay', 'builder', True),
		('cd /tmp/archinstall-yay && makepkg --syncdeps --install --needed --noconfirm', 'builder', True),
	]
	expected_sudoers = (
		'builder ALL=(root) NOPASSWD: /usr/bin/pacman --noconfirm -S --asdeps *\nbuilder ALL=(root) NOPASSWD: /usr/bin/pacman --noconfirm -U --needed *\n'
	)
	assert installer.sudoers_snapshots == [expected_sudoers, expected_sudoers, expected_sudoers, expected_sudoers]
	assert not list((tmp_path / 'etc/sudoers.d').glob('99-archinstall-aur-builder-*'))


def test_aura_uses_source_package(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	users = [User('builder', Password(enc_password='test'), sudo=True)]

	AurHelperApp().install(installer, AurHelperConfiguration(AurHelper.AURA), users)  # type: ignore[arg-type]

	assert installer.commands[2] == (
		'git clone --depth=1 https://aur.archlinux.org/aura.git /tmp/archinstall-aura',
		'builder',
		True,
	)


def test_aur_helper_requires_non_root_user(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	with pytest.raises(ValueError, match='non-root user'):
		AurHelperApp().install(installer, AurHelperConfiguration(AurHelper.PIKAUR), None)  # type: ignore[arg-type]


def test_aur_helper_removes_temporary_sudoers_after_failure(tmp_path: Path) -> None:
	installer = FailingInstaller(tmp_path)
	users = [User('builder', Password(enc_password='test'), sudo=True)]

	with pytest.raises(RuntimeError, match='AUR build failed'):
		AurHelperApp().install(installer, AurHelperConfiguration(AurHelper.AURA), users)  # type: ignore[arg-type]

	assert not list((tmp_path / 'etc/sudoers.d').glob('99-archinstall-aur-builder-*'))


def test_aur_helper_does_not_overwrite_existing_sudoers_file(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	users = [User('builder', Password(enc_password='test'), sudo=True)]
	legacy_path = tmp_path / 'etc/sudoers.d/99-archinstall-aur-builder'
	legacy_path.parent.mkdir(parents=True)
	legacy_path.write_text('existing rule\n')
	legacy_path.chmod(0o400)

	AurHelperApp().install(installer, AurHelperConfiguration(AurHelper.PARU), users)  # type: ignore[arg-type]

	assert legacy_path.read_text() == 'existing rule\n'
	assert legacy_path.stat().st_mode & 0o777 == 0o400


def test_aur_helper_cleans_stale_build_directory_before_clone(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	users = [User('builder', Password(enc_password='test'), sudo=True)]

	AurHelperApp().install(installer, AurHelperConfiguration(AurHelper.PIKAUR), users)  # type: ignore[arg-type]

	assert installer.commands[0] == ('rm -rf -- /tmp/archinstall-pikaur', None, False)
	assert installer.commands[1] == ('install -d -m 0700 -o builder -- /tmp/archinstall-pikaur', None, False)
	assert installer.commands[2][0].startswith('git clone --depth=1 https://aur.archlinux.org/pikaur.git')
