from typing import cast

from archinstall.lib.general.kernel_packages import installer_base_packages
from archinstall.lib.models.application import FirmwarePackageMode, FirmwarePackagesConfiguration, FirmwareVendor


def test_malformed_firmware_mode_fails_safe_to_full_set() -> None:
	config = FirmwarePackagesConfiguration()
	config.mode = cast(FirmwarePackageMode, 'unknown-mode')

	assert installer_base_packages(config) == [
		'base',
		'sudo',
		'linux-firmware',
		'mkinitcpio',
	]


def test_malformed_firmware_vendor_fails_safe_to_full_set() -> None:
	config = FirmwarePackagesConfiguration(mode=FirmwarePackageMode.VENDOR)
	config.vendors = cast(list[FirmwareVendor], ['unknown-vendor'])

	assert installer_base_packages(config) == [
		'base',
		'sudo',
		'linux-firmware',
		'mkinitcpio',
	]
