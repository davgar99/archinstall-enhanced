from typing import TYPE_CHECKING

from archinstall.lib.log import debug
from archinstall.lib.models.gaming import NTSyncConfiguration

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


class NTSyncApp:
	@property
	def packages(self) -> list[str]:
		return ['ntsync-autoload']

	def install(self, install_session: Installer, ntsync_config: NTSyncConfiguration) -> None:
		if not ntsync_config.enabled:
			return

		debug('Installing NTSYNC autoload support')
		install_session.add_additional_packages(self.packages)
