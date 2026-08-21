from typing import TYPE_CHECKING, ClassVar

from archinstall.lib.exceptions import RequirementError
from archinstall.lib.hardware import CPUVendor, SysInfo
from archinstall.lib.log import debug, warn
from archinstall.lib.models.gaming import GamingConfiguration

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


class HardwareWatchdogApp:
	_MODULES: ClassVar[dict[CPUVendor, str]] = {
		CPUVendor.AMD: 'sp5100_tco',
		CPUVendor.INTEL: 'iTCO_wdt',
	}

	def module(self, vendor: CPUVendor | None = None) -> str | None:
		resolved_vendor = vendor if vendor is not None else SysInfo.cpu_vendor()
		if resolved_vendor is None:
			return None
		return self._MODULES.get(resolved_vendor)

	def install(self, install_session: Installer, gaming_config: GamingConfiguration) -> None:
		if gaming_config.disable_watchdog is not True:
			return

		module = self.module()
		if module is None:
			warn('Could not disable hardware watchdog: unsupported or unknown CPU vendor')
			return

		debug(f'Disabling hardware watchdog module: {module}')
		config_path = install_session.target / 'etc/modprobe.d/disable-watchdog.conf'
		config_path.parent.mkdir(parents=True, exist_ok=True)
		config_path.write_text(f'blacklist {module}\n')

		# The blacklist must be in place before the initramfs is (re)built, otherwise a
		# watchdog module already pulled in by mkinitcpio's autodetect hook would still
		# load at early boot despite the blacklist now present on disk.
		if not install_session.mkinitcpio(['-P']):
			raise RequirementError('Failed to rebuild initramfs after disabling hardware watchdog')
