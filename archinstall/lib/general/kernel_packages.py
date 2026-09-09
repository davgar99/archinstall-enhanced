from archinstall.lib.models.application import FirmwarePackageMode, FirmwarePackagesConfiguration

DEFAULT_BASE_PACKAGES = ['base', 'sudo', 'linux-firmware', 'mkinitcpio']


def kernel_header_packages(kernels: list[str]) -> list[str]:
	"""Return matching Arch kernel header packages while preserving selection order."""
	return list(dict.fromkeys(f'{kernel}-headers' for kernel in kernels))


def installer_base_packages(firmware_config: FirmwarePackagesConfiguration | None) -> list[str] | None:
	"""Build the bootstrap package list for an explicit firmware policy.

	Returning ``None`` preserves Installer's historical default package set.
	A vendor policy without vendors is invalid but can still arrive through a
	manually constructed or legacy configuration. Fail safe to the complete
	firmware set rather than producing an installation with no firmware.
	"""
	if firmware_config is None:
		return None

	firmware_packages = firmware_config.packages()
	if firmware_config.mode == FirmwarePackageMode.VENDOR and not firmware_packages:
		return DEFAULT_BASE_PACKAGES.copy()

	packages = ['base', 'sudo', 'mkinitcpio', *firmware_packages]
	return list(dict.fromkeys(packages))
