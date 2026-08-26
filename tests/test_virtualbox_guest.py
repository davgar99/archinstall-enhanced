from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from archinstall.applications.virtualbox_guest import VirtualBoxGuestApp
from archinstall.lib.hardware import GfxDriver, SysInfo
from archinstall.lib.models.users import Password, User
from archinstall.lib.profile.profiles_handler import ProfileHandler


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


def test_virtualbox_graphics_preview_explains_detected_guest_integration(monkeypatch: MonkeyPatch) -> None:
	monkeypatch.setattr(SysInfo, 'virtualization', lambda: 'oracle')
	preview = GfxDriver.VMOpenSource.packages_text()

	assert 'mesa' in preview
	assert 'virtualbox-guest-utils' in preview
	assert 'VirtualBox was detected' not in preview


def test_virtualbox_graphics_preview_omits_guest_package_on_other_hypervisors(monkeypatch: MonkeyPatch) -> None:
	monkeypatch.setattr(SysInfo, 'virtualization', lambda: 'kvm')
	preview = GfxDriver.VMOpenSource.packages_text()

	assert 'virtualbox-guest-utils' not in preview
	assert 'Guest Additions will not be installed' in preview


def test_virtualbox_profile_installs_guest_package_only_when_detected(monkeypatch: MonkeyPatch) -> None:
	installer = MagicMock()
	installer.kernels = ['linux']
	monkeypatch.setattr(SysInfo, 'virtualization', lambda: 'oracle')

	ProfileHandler().install_gfx_driver(installer, GfxDriver.VMOpenSource)

	installer.add_additional_packages.assert_called_once_with(['mesa-utils', 'vulkan-tools', 'libva-utils', 'mesa', 'virtualbox-guest-utils'])


def test_virtualbox_profile_omits_guest_package_on_kvm(monkeypatch: MonkeyPatch) -> None:
	installer = MagicMock()
	installer.kernels = ['linux']
	monkeypatch.setattr(SysInfo, 'virtualization', lambda: 'kvm')

	ProfileHandler().install_gfx_driver(installer, GfxDriver.VMOpenSource)

	installer.add_additional_packages.assert_called_once_with(['mesa-utils', 'vulkan-tools', 'libva-utils', 'mesa'])


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
