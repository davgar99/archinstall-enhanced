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

	def add_additional_packages(self, packages: list[str]) -> None:
		self.packages.extend(packages)

	def arch_chroot(self, command: str, run_as: str | None = None, peek_output: bool = False) -> None:
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
		('git clone --depth=1 https://aur.archlinux.org/yay.git /tmp/archinstall-yay', 'builder', True),
		('cd /tmp/archinstall-yay && makepkg --syncdeps --install --needed --noconfirm', 'builder', True),
	]
	assert not (tmp_path / 'etc/sudoers.d/99-archinstall-aur-builder').exists()


def test_aur_helper_requires_non_root_user(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	with pytest.raises(ValueError, match='non-root user'):
		AurHelperApp().install(installer, AurHelperConfiguration(AurHelper.PIKAUR), None)  # type: ignore[arg-type]


def test_aur_helper_removes_temporary_sudoers_after_failure(tmp_path: Path) -> None:
	installer = FailingInstaller(tmp_path)
	users = [User('builder', Password(enc_password='test'), sudo=True)]

	with pytest.raises(RuntimeError, match='AUR build failed'):
		AurHelperApp().install(installer, AurHelperConfiguration(AurHelper.AURA), users)  # type: ignore[arg-type]

	assert not (tmp_path / 'etc/sudoers.d/99-archinstall-aur-builder').exists()
