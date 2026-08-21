from typing import TYPE_CHECKING

from archinstall.applications.cpu_scheduler import CPUSchedulerApp
from archinstall.applications.gaming_compatibility import GamingCompatibilityApp
from archinstall.applications.gaming_tools import GamingToolsApp
from archinstall.applications.graphics_extras import GraphicsExtrasApp
from archinstall.applications.hardware_watchdog import HardwareWatchdogApp
from archinstall.applications.ntsync import NTSyncApp
from archinstall.applications.playstation_controller import PlayStationControllerApp
from archinstall.lib.hardware import GfxDriver
from archinstall.lib.models.gaming import GamingConfiguration

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer
	from archinstall.lib.models.users import User


class GamingHandler:
	def install_gaming(
		self,
		install_session: Installer,
		gaming_config: GamingConfiguration,
		users: list[User] | None = None,
		gfx_driver: GfxDriver | None = None,
	) -> None:
		if gaming_config.cpu_scheduler_config:
			CPUSchedulerApp().install(install_session, gaming_config.cpu_scheduler_config)

		if gaming_config.ntsync_config:
			NTSyncApp().install(install_session, gaming_config.ntsync_config)

		GamingToolsApp().install(install_session, gaming_config, users)
		GamingCompatibilityApp().install(install_session, gaming_config)
		HardwareWatchdogApp().install(install_session, gaming_config)
		GraphicsExtrasApp().install(install_session, gaming_config, gfx_driver)
		PlayStationControllerApp().install(install_session, gaming_config)
