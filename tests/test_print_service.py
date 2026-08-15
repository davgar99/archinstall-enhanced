from pathlib import Path

from archinstall.applications.print_service import PrintServiceApp


class FakeInstaller:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.packages: list[str] = []
		self.services: list[str] = []

	def add_additional_packages(self, packages: list[str]) -> None:
		self.packages.extend(packages)

	def enable_service(self, services: list[str]) -> None:
		self.services.extend(services)


def test_enable_mdns_resolution_inserts_before_resolve(tmp_path: Path) -> None:
	nsswitch_conf = tmp_path / 'etc/nsswitch.conf'
	nsswitch_conf.parent.mkdir(parents=True)
	nsswitch_conf.write_text('hosts: mymachines resolve [!UNAVAIL=return] files myhostname dns\n')

	PrintServiceApp().install(FakeInstaller(tmp_path))  # type: ignore[arg-type]

	assert nsswitch_conf.read_text() == 'hosts: mymachines mdns_minimal [NOTFOUND=return] resolve [!UNAVAIL=return] files myhostname dns\n'


def test_enable_mdns_resolution_is_idempotent(tmp_path: Path) -> None:
	nsswitch_conf = tmp_path / 'etc/nsswitch.conf'
	nsswitch_conf.parent.mkdir(parents=True)
	content = 'hosts: mymachines mdns_minimal [NOTFOUND=return] resolve [!UNAVAIL=return] files myhostname dns\n'
	nsswitch_conf.write_text(content)

	PrintServiceApp().install(FakeInstaller(tmp_path))  # type: ignore[arg-type]

	assert nsswitch_conf.read_text() == content


def test_enable_mdns_resolution_skips_missing_file(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	PrintServiceApp().install(installer)  # type: ignore[arg-type]

	assert not (tmp_path / 'etc/nsswitch.conf').exists()
	assert installer.packages


def test_enable_mdns_resolution_fallback_dns(tmp_path: Path) -> None:
	nsswitch_conf = tmp_path / 'etc/nsswitch.conf'
	nsswitch_conf.parent.mkdir(parents=True)
	nsswitch_conf.write_text('hosts: files mymachines dns\n')

	PrintServiceApp().install(FakeInstaller(tmp_path))  # type: ignore[arg-type]

	assert nsswitch_conf.read_text() == 'hosts: files mymachines mdns_minimal [NOTFOUND=return] dns\n'


def test_enable_mdns_resolution_only_inspects_hosts_database(tmp_path: Path) -> None:
	nsswitch_conf = tmp_path / 'etc/nsswitch.conf'
	nsswitch_conf.parent.mkdir(parents=True)
	nsswitch_conf.write_text('passwd: files resolve\nhosts: files dns\n')

	PrintServiceApp().install(FakeInstaller(tmp_path))  # type: ignore[arg-type]

	assert nsswitch_conf.read_text() == 'passwd: files resolve\nhosts: files mdns_minimal [NOTFOUND=return] dns\n'


def test_enable_mdns_resolution_keeps_files_first(tmp_path: Path) -> None:
	nsswitch_conf = tmp_path / 'etc/nsswitch.conf'
	nsswitch_conf.parent.mkdir(parents=True)
	nsswitch_conf.write_text('hosts: files\n')

	PrintServiceApp().install(FakeInstaller(tmp_path))  # type: ignore[arg-type]

	assert nsswitch_conf.read_text() == 'hosts: files mdns_minimal [NOTFOUND=return]\n'


def test_enable_mdns_resolution_ignores_inline_comment(tmp_path: Path) -> None:
	nsswitch_conf = tmp_path / 'etc/nsswitch.conf'
	nsswitch_conf.parent.mkdir(parents=True)
	nsswitch_conf.write_text('  hosts: files dns # resolve and mdns_minimal are optional\n')

	PrintServiceApp().install(FakeInstaller(tmp_path))  # type: ignore[arg-type]

	assert nsswitch_conf.read_text() == '  hosts: files mdns_minimal [NOTFOUND=return] dns # resolve and mdns_minimal are optional\n'


def test_enable_mdns_resolution_does_not_consume_next_database(tmp_path: Path) -> None:
	nsswitch_conf = tmp_path / 'etc/nsswitch.conf'
	nsswitch_conf.parent.mkdir(parents=True)
	nsswitch_conf.write_text('hosts:\nnetworks: files\n')

	PrintServiceApp().install(FakeInstaller(tmp_path))  # type: ignore[arg-type]

	assert nsswitch_conf.read_text() == 'hosts: mdns_minimal [NOTFOUND=return]\nnetworks: files\n'
