from typing import TYPE_CHECKING

from archinstall.lib.log import debug
from archinstall.lib.models.application import FirmwareConfiguration

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


class FirmwareApp:
	@property
	def packages(self) -> list[str]:
		return ['fwupd']

	@property
	def services(self) -> list[str]:
		return ['fwupd-refresh.timer']

	def install(self, install_session: Installer, firmware_config: FirmwareConfiguration) -> None:
		if not firmware_config.enabled:
			return

		debug('Installing firmware update support')
		install_session.add_additional_packages(self.packages)
		install_session.enable_service(self.services)
