from pathlib import Path

import pytest
from pytest import MonkeyPatch

from archinstall.applications.virtualbox_guest import VirtualBoxGuestApp
from archinstall.lib.hardware import SysInfo
from archinstall.lib.models.users import Password, User


class FakeInstaller:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.packages: list[str] = []
		self.services: list[str] = []
		self.chroot_commands: list[str] = []

	def add_additional_packages(self, packages: str) -> None:
		self.packages.append(packages)

	def enable_service(self, service: str) -> None:
		self.services.append(service)

	def arch_chroot(self, command: str) -> None:
		self.chroot_commands.append(command)


@pytest.mark.parametrize(
	('virtualization', 'expected'),
	[('oracle', True), ('kvm', False), ('qemu', False), ('vmware', False), ('none', False)],
)
def test_virtualbox_detection_is_exclusive(virtualization: str, expected: bool, monkeypatch: MonkeyPatch) -> None:
	monkeypatch.setattr(SysInfo, 'virtualization', lambda: virtualization)

	assert VirtualBoxGuestApp.detected() is expected


def test_virtualbox_guest_integration(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	users = [
		User('david', Password(enc_password='test'), sudo=True),
		User('gaming user', Password(enc_password='test'), sudo=False),
	]

	VirtualBoxGuestApp().install(installer, users)  # type: ignore[arg-type]

	assert installer.packages == ['virtualbox-guest-utils']
	assert installer.services == ['vboxservice.service']
	assert installer.chroot_commands == [
		'usermod -aG vboxsf david',
		"usermod -aG vboxsf 'gaming user'",
	]
