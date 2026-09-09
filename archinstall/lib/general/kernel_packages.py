from archinstall.lib.models.application import FirmwarePackagesConfiguration

DEFAULT_BASE_PACKAGES = ['base', 'sudo', 'linux-firmware', 'mkinitcpio']


def kernel_header_packages(kernels: list[str]) -> list[str]:
	"""Return matching Arch kernel header packages while preserving selection order."""
	return list(dict.fromkeys(f'{kernel}-headers' for kernel in kernels))


def installer_base_packages(firmware_config: FirmwarePackagesConfiguration | None) -> list[str] | None:
	"""Build the bootstrap package list for an explicit firmware policy.

	Returning ``None`` preserves Installer's historical default package set.
	"""
	if firmware_config is None:
		return None

	packages = ['base', 'sudo', 'mkinitcpio', *firmware_config.packages()]
	return list(dict.fromkeys(packages))
