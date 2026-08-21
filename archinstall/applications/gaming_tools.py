import shlex
from typing import TYPE_CHECKING

from archinstall.lib.exceptions import SysCallError
from archinstall.lib.hardware import GfxDriver
from archinstall.lib.log import debug, warn
from archinstall.lib.models.gaming import GamingConfiguration

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer
	from archinstall.lib.models.users import User


class GamingToolsApp:
	def steam_runtime_packages(self, gfx_driver: GfxDriver | None) -> list[str]:
		# Steam depends on virtual ttf-font, vulkan-driver and lib32-vulkan-driver
		# providers. The native Vulkan provider is installed by the graphics
		# profile before this app runs; install the matching 32-bit provider here
		# so pacstrap --noconfirm cannot silently choose a mismatched GPU stack.
		packages = ['ttf-liberation']

		match gfx_driver:
			case GfxDriver.AmdOpenSource:
				packages.extend(['lib32-mesa', 'lib32-vulkan-radeon'])
			case GfxDriver.IntelOpenSource:
				packages.extend(['lib32-mesa', 'lib32-vulkan-intel'])
			case GfxDriver.NvidiaOpenKernel:
				packages.append('lib32-nvidia-utils')
			case GfxDriver.NvidiaOpenSource:
				packages.extend(['lib32-mesa', 'lib32-vulkan-nouveau'])
			case GfxDriver.AllOpenSource:
				packages.extend(
					[
						'lib32-mesa',
						'lib32-vulkan-radeon',
						'lib32-vulkan-intel',
						'lib32-vulkan-nouveau',
					]
				)
			case GfxDriver.VMOpenSource:
				packages.extend(['lib32-mesa', 'lib32-vulkan-swrast'])
			case None:
				warn(
					'Steam was selected without an explicit graphics driver. '
					'Pacman may need to choose a Vulkan provider automatically.',
				)

		return packages

	def packages(self, gaming_config: GamingConfiguration, gfx_driver: GfxDriver | None = None) -> list[str]:
		packages: list[str] = []

		if gaming_config.steam:
			packages.extend(self.steam_runtime_packages(gfx_driver))
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
		gfx_driver: GfxDriver | None = None,
	) -> None:
		packages = self.packages(gaming_config, gfx_driver)
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
