from archinstall.lib.applications.application_handler import ApplicationHandler
from archinstall.lib.general.kernel_packages import installer_base_packages, kernel_header_packages
from archinstall.lib.hardware import GfxDriver
from archinstall.lib.models.application import (
	ApplicationConfiguration,
	FirmwarePackageMode,
	FirmwarePackagesConfiguration,
	FirmwareVendor,
	KernelHeadersConfiguration,
)
from archinstall.lib.profile.profiles_handler import ProfileHandler


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
