import asyncio

from pytest import MonkeyPatch

from archinstall.lib.applications.application_handler import ApplicationHandler
from archinstall.lib.applications.application_menu import select_firmware_packages
from archinstall.lib.general.kernel_packages import installer_base_packages, kernel_header_packages
from archinstall.lib.hardware import GfxDriver
from archinstall.lib.menu.helpers import Notify, Selection
from archinstall.lib.models.application import (
	ApplicationConfiguration,
	FirmwarePackageMode,
	FirmwarePackagesConfiguration,
	FirmwareVendor,
	KernelHeadersConfiguration,
)
from archinstall.lib.profile.profiles_handler import ProfileHandler
from archinstall.tui.result import Result


class FakeInstaller:
	def __init__(self, kernels: list[str]) -> None:
		self.kernels = kernels
		self.packages: list[str] = []

	def add_additional_packages(self, packages: str | list[str]) -> None:
		if isinstance(packages, str):
			packages = [packages]
		self.packages.extend(packages)


def test_kernel_header_packages_follow_every_selected_kernel() -> None:
	assert kernel_header_packages(['linux', 'linux-lts', 'linux-zen']) == [
		'linux-headers',
		'linux-lts-headers',
		'linux-zen-headers',
	]


def test_firmware_policy_defaults_and_vendor_packages() -> None:
	assert installer_base_packages(None) is None
	assert installer_base_packages(FirmwarePackagesConfiguration(mode=FirmwarePackageMode.MINIMAL)) == ['base', 'sudo', 'mkinitcpio']
	assert installer_base_packages(
		FirmwarePackagesConfiguration(
			mode=FirmwarePackageMode.VENDOR,
			vendors=[FirmwareVendor.INTEL, FirmwareVendor.REALTEK],
		)
	) == ['base', 'sudo', 'mkinitcpio', 'linux-firmware-intel', 'linux-firmware-realtek']


def test_empty_vendor_firmware_config_fails_safe_to_full_set() -> None:
	assert installer_base_packages(FirmwarePackagesConfiguration(mode=FirmwarePackageMode.VENDOR)) == [
		'base',
		'sudo',
		'linux-firmware',
		'mkinitcpio',
	]


def test_application_handler_installs_explicit_kernel_headers() -> None:
	installer = FakeInstaller(['linux', 'linux-lts'])
	config = ApplicationConfiguration(kernel_headers_config=KernelHeadersConfiguration(enabled=True))
	ApplicationHandler().install_applications(installer, config)  # type: ignore[arg-type]
	assert installer.packages == ['linux-headers', 'linux-lts-headers']


def test_nvidia_open_multi_kernel_path_uses_dkms_and_all_headers() -> None:
	installer = FakeInstaller(['linux', 'linux-lts'])
	ProfileHandler().install_gfx_driver(installer, GfxDriver.NvidiaOpenKernel)  # type: ignore[arg-type]
	assert 'nvidia-open-dkms' in installer.packages
	assert 'dkms' in installer.packages
	assert 'linux-headers' in installer.packages
	assert 'linux-lts-headers' in installer.packages


def test_firmware_policy_round_trip() -> None:
	config = ApplicationConfiguration(
		firmware_packages_config=FirmwarePackagesConfiguration(
			mode=FirmwarePackageMode.VENDOR,
			vendors=[FirmwareVendor.AMD_GPU, FirmwareVendor.NVIDIA],
		)
	)
	parsed = ApplicationConfiguration.parse_arg(dict(config.json()))
	assert parsed.firmware_packages_config is not None
	assert parsed.firmware_packages_config.mode == FirmwarePackageMode.VENDOR
	assert parsed.firmware_packages_config.vendors == [FirmwareVendor.AMD_GPU, FirmwareVendor.NVIDIA]


def test_vendor_mode_reprompts_on_empty_selection(monkeypatch: MonkeyPatch) -> None:
	selection_calls = 0
	notifications = 0

	async def show_selection(_selection: Selection[object]) -> Result[object]:
		nonlocal selection_calls
		selection_calls += 1
		if selection_calls == 1:
			return Result.selection(FirmwarePackageMode.VENDOR)
		if selection_calls == 2:
			return Result.selection([])
		return Result.selection([FirmwareVendor.INTEL])

	async def show_notify(_notify: Notify) -> Result[bool]:
		nonlocal notifications
		notifications += 1
		return Result.true()

	monkeypatch.setattr(Selection, 'show', show_selection)
	monkeypatch.setattr(Notify, 'show', show_notify)

	result = asyncio.run(select_firmware_packages(preset=None))
	assert result is not None
	assert result.mode == FirmwarePackageMode.VENDOR
	assert result.vendors == [FirmwareVendor.INTEL]
	assert selection_calls == 3
	assert notifications == 1


def test_vendor_mode_skip_with_no_preset_falls_back_to_full(monkeypatch: MonkeyPatch) -> None:
	selection_calls = 0
	notifications = 0

	async def show_selection(_selection: Selection[object]) -> Result[object]:
		nonlocal selection_calls
		selection_calls += 1
		if selection_calls == 1:
			return Result.selection(FirmwarePackageMode.VENDOR)
		return Result.skip()

	async def show_notify(_notify: Notify) -> Result[bool]:
		nonlocal notifications
		notifications += 1
		return Result.true()

	monkeypatch.setattr(Selection, 'show', show_selection)
	monkeypatch.setattr(Notify, 'show', show_notify)

	result = asyncio.run(select_firmware_packages(preset=None))
	assert result is not None
	assert result.mode == FirmwarePackageMode.FULL
	assert result.vendors == []
	assert selection_calls == 2
	assert notifications == 1
