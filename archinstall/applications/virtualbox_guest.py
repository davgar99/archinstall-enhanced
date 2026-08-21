import shlex
from typing import TYPE_CHECKING

from archinstall.lib.exceptions import SysCallError
from archinstall.lib.hardware import SysInfo
from archinstall.lib.log import debug, warn

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer
	from archinstall.lib.models.users import User


class VirtualBoxGuestApp:
	@staticmethod
	def detected() -> bool:
		return SysInfo.virtualization() == 'oracle'

	def install(self, install_session: Installer, users: list[User] | None = None, install_package: bool = True) -> None:
		debug('Installing VirtualBox Guest Additions integration')
		if install_package:
			install_session.add_additional_packages('virtualbox-guest-utils')
		install_session.enable_service('vboxservice.service')

		for user in users or []:
			username = shlex.quote(user.username)
			try:
				install_session.arch_chroot(f'usermod -aG vboxsf {username}')
			except SysCallError as err:
				warn(f'Failed to add {user.username} to group vboxsf: {err}')
