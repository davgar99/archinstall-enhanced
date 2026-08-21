import re
from typing import TYPE_CHECKING

from archinstall.lib.log import debug
from archinstall.lib.models.network import DnsResolver

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


class PrintServiceApp:
	def packages(self, dns_resolver: DnsResolver) -> list[str]:
		packages = ['cups', 'system-config-printer', 'cups-pk-helper', 'ghostscript', 'avahi']
		if dns_resolver != DnsResolver.SYSTEMD_RESOLVED:
			packages.append('nss-mdns')
		return packages

	@property
	def services(self) -> list[str]:
		return [
			'cups.service',
			'avahi-daemon.service',
		]

	def install(self, install_session: Installer, dns_resolver: DnsResolver = DnsResolver.DEFAULT) -> None:
		debug('Installing print service')
		install_session.add_additional_packages(self.packages(dns_resolver))
		install_session.enable_service(self.services)
		if dns_resolver != DnsResolver.SYSTEMD_RESOLVED:
			self._enable_mdns_resolution(install_session)

	def _enable_mdns_resolution(self, install_session: Installer) -> None:
		nsswitch_conf = install_session.target / 'etc/nsswitch.conf'
		if not nsswitch_conf.exists():
			return

		content = nsswitch_conf.read_text()
		hosts_match = re.search(r'^([ \t]*hosts:[ \t]*)([^\r\n]*)', content, flags=re.MULTILINE)
		if hosts_match is None:
			return

		prefix, services = hosts_match.groups()
		service_entries, comment_marker, comment = services.partition('#')
		if re.search(r'\bmdns_minimal\b', service_entries):
			return

		if 'resolve [!UNAVAIL=return]' in service_entries:
			new_service_entries = service_entries.replace(
				'resolve [!UNAVAIL=return]',
				'mdns_minimal [NOTFOUND=return] resolve [!UNAVAIL=return]',
				1,
			)
		elif re.search(r'\bresolve\b', service_entries):
			new_service_entries = re.sub(
				r'\bresolve\b',
				'mdns_minimal [NOTFOUND=return] resolve',
				service_entries,
				count=1,
			)
		elif re.search(r'\bdns\b', service_entries):
			new_service_entries = re.sub(
				r'\bdns\b',
				'mdns_minimal [NOTFOUND=return] dns',
				service_entries,
				count=1,
			)
		elif re.search(r'\bfiles\b', service_entries):
			new_service_entries = re.sub(
				r'\bfiles\b',
				'files mdns_minimal [NOTFOUND=return]',
				service_entries,
				count=1,
			)
		else:
			needs_separator = not (service_entries[-1:].isspace() or (not service_entries and prefix[-1:].isspace()))
			separator = ' ' if needs_separator else ''
			new_service_entries = f'{service_entries}{separator}mdns_minimal [NOTFOUND=return]'

		new_services = new_service_entries + comment_marker + comment
		new_content = content[: hosts_match.start()] + prefix + new_services + content[hosts_match.end() :]
		nsswitch_conf.write_text(new_content)
