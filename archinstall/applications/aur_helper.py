import secrets
import shlex
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from archinstall.lib.log import debug
from archinstall.lib.models.application import AurHelper, AurHelperConfiguration

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer
	from archinstall.lib.models.users import User


class AurHelperApp:
	_PACKAGES: ClassVar[dict[AurHelper, str]] = {
		AurHelper.YAY: 'yay',
		AurHelper.PARU: 'paru',
		AurHelper.PIKAUR: 'pikaur',
		AurHelper.AURA: 'aura',
	}

	def install(
		self,
		install_session: Installer,
		config: AurHelperConfiguration,
		users: list[User] | None,
	) -> None:
		if not users:
			raise ValueError('An AUR helper requires a configured non-root user')

		build_user = next((user for user in users if user.sudo), users[0])
		username = build_user.username
		helper = config.aur_helper
		package = self._PACKAGES[helper]
		build_dir = f'/tmp/archinstall-{package}'
		sudoers_path = self._temporary_sudoers_path(install_session.target)

		debug(f'Building and installing AUR helper {package} as {username}')
		install_session.add_additional_packages(['base-devel', 'git'])
		self._write_temporary_sudoers(sudoers_path, username)

		try:
			# A failed or interrupted prior build can leave this directory behind.
			# Remove only the installer-controlled path before cloning so retries are idempotent.
			install_session.arch_chroot(f'rm -rf -- {shlex.quote(build_dir)}')
			install_session.arch_chroot(
				f'git clone --depth=1 https://aur.archlinux.org/{package}.git {shlex.quote(build_dir)}',
				run_as=username,
				peek_output=True,
			)
			install_session.arch_chroot(
				f'cd {shlex.quote(build_dir)} && makepkg --syncdeps --install --needed --noconfirm',
				run_as=username,
				peek_output=True,
			)
		finally:
			sudoers_path.unlink(missing_ok=True)

	@staticmethod
	def _temporary_sudoers_path(target: Path) -> Path:
		sudoers_dir = target / 'etc/sudoers.d'
		sudoers_dir.mkdir(parents=True, exist_ok=True)
		return sudoers_dir / f'99-archinstall-aur-builder-{secrets.token_hex(8)}'

	@staticmethod
	def _write_temporary_sudoers(path: Path, username: str) -> None:
		path.write_text(
			f'{username} ALL=(root) NOPASSWD: /usr/bin/pacman --noconfirm -S --asdeps *\n'
			f'{username} ALL=(root) NOPASSWD: /usr/bin/pacman --noconfirm -U --needed *\n'
		)
		path.chmod(0o440)
