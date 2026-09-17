from typing import TYPE_CHECKING

from archinstall.lib.log import debug
from archinstall.lib.models.gaming import GamingConfiguration

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


class NowatchdogApp:
	"""Adds the 'nowatchdog' kernel parameter, turning off the NMI hard/soft lockup detectors.

	This only disables that debugging feature; it does not touch the hardware watchdog timer,
	so a genuinely hung system can still be force-rebooted.
	"""

	def install(self, install_session: Installer, gaming_config: GamingConfiguration) -> None:
		if gaming_config.nowatchdog is not True:
			return

		debug('Disabling NMI hard/soft lockup detectors with the nowatchdog kernel parameter')
		install_session.add_kernel_params(['nowatchdog'])
