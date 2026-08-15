from typing import TYPE_CHECKING

from archinstall.lib.log import debug

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


class PrintServiceApp:
	@property
	def packages(self) -> list[str]:
		return ['cups', 'system-config-printer', 'cups-pk-helper', 'ghostscript', 'avahi', 'nss-mdns']

	@property
	def services(self) -> list[str]:
		return [
			'cups.service',
			'avahi-daemon.service',
		]

	def install(self, install_session: Installer) -> None:
		debug('Installing print service')
		install_session.add_additional_packages(self.packages)
		install_session.enable_service(self.services)
		self._enable_mdns_resolution(install_session)

	def _enable_mdns_resolution(self, install_session: Installer) -> None:
		nsswitch_conf = install_session.target / 'etc/nsswitch.conf'
		if not nsswitch_conf.exists():
			return

		content = nsswitch_conf.read_text()

		if 'mdns_minimal' not in content:
			nsswitch_conf.write_text(
				content.replace(
					'resolve [!UNAVAIL=return]',
					'mdns_minimal [NOTFOUND=return] resolve [!UNAVAIL=return]',
				)
			)
