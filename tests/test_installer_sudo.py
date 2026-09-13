import stat
from pathlib import Path

from archinstall.lib.installer import Installer
from archinstall.lib.models.users import Password, User


def test_enable_sudo_creates_traversable_sudoers_directory(tmp_path: Path) -> None:
	etc = tmp_path / 'etc'
	etc.mkdir()
	(etc / 'sudoers').write_text('')

	installer = object.__new__(Installer)
	installer.target = tmp_path
	user = User('alice', Password(enc_password='$test$hash'), sudo=True)

	installer.enable_sudo(user)

	sudoers_dir = etc / 'sudoers.d'
	rule_file = sudoers_dir / '00_alice'
	assert stat.S_IMODE(sudoers_dir.stat().st_mode) == 0o750
	assert stat.S_IMODE(rule_file.stat().st_mode) == 0o440
	assert '@includedir /etc/sudoers.d\n' in (etc / 'sudoers').read_text()
