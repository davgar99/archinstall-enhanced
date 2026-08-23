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
		sudoers_path = install_session.target / 'etc/sudoers.d/99-archinstall-aur-builder'
		original_contents = sudoers_path.read_bytes() if sudoers_path.exists() else None
		original_mode = sudoers_path.stat().st_mode & 0o777 if sudoers_path.exists() else None

		debug(f'Building and installing AUR helper {package} as {username}')
		install_session.add_additional_packages(['base-devel', 'git'])
		self._write_temporary_sudoers(sudoers_path, username)

		try:
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
			if original_contents is None:
				sudoers_path.unlink(missing_ok=True)
			else:
				sudoers_path.write_bytes(original_contents)
				if original_mode is not None:
					sudoers_path.chmod(original_mode)

	@staticmethod
	def _write_temporary_sudoers(path: Path, username: str) -> None:
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(
			f'{username} ALL=(root) NOPASSWD: /usr/bin/pacman --noconfirm -S --asdeps *\n'
			f'{username} ALL=(root) NOPASSWD: /usr/bin/pacman --noconfirm -U --needed *\n'
		)
		path.chmod(0o440)
