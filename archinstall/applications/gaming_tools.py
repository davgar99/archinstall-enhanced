import shlex
from typing import TYPE_CHECKING

from archinstall.lib.exceptions import SysCallError
from archinstall.lib.log import debug, warn
from archinstall.lib.models.gaming import GamingConfiguration

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer
	from archinstall.lib.models.users import User


class GamingToolsApp:
	def packages(self, gaming_config: GamingConfiguration) -> list[str]:
		packages: list[str] = []

		if gaming_config.steam:
			packages.append('steam')

		if gaming_config.protontricks:
			packages.append('protontricks')

		if gaming_config.gamemode:
			packages.extend(['gamemode', 'lib32-gamemode'])

		if gaming_config.mangohud:
			packages.extend(['mangohud', 'lib32-mangohud'])

		if gaming_config.gamescope:
			packages.append('gamescope')

		return packages

	def install(
		self,
		install_session: Installer,
		gaming_config: GamingConfiguration,
		users: list[User] | None = None,
	) -> None:
		packages = self.packages(gaming_config)
		if packages:
			debug(f'Installing gaming tools: {packages}')
			install_session.add_additional_packages(packages)

		if gaming_config.gamemode:
			for user in users or []:
				username = shlex.quote(user.username)
				try:
					install_session.arch_chroot(f'usermod -aG gamemode {username}')
				except SysCallError as err:
					warn(f'Failed to add {user.username} to group gamemode: {err}')
