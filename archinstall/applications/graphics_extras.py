from typing import TYPE_CHECKING

from archinstall.lib.hardware import GfxDriver
from archinstall.lib.log import debug, warn
from archinstall.lib.models.gaming import GamingConfiguration

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


class GraphicsExtrasApp:
	def packages(self, config: GamingConfiguration, driver: GfxDriver | None) -> list[str]:
		if driver is None:
			return []

		packages: list[str] = []
		if config.install_32bit_graphics:
			packages.extend(self._multilib_packages(driver))
		if config.install_opencl:
			packages.extend(self._opencl_packages(driver, config.install_32bit_graphics is True))
		return list(dict.fromkeys(packages))

	def install(self, install_session: Installer, config: GamingConfiguration, driver: GfxDriver | None) -> None:
		if driver is None and (config.install_32bit_graphics or config.install_opencl):
			warn('Skipping graphics extras because no graphics driver was selected')
			return

		packages = self.packages(config, driver)
		if packages:
			debug(f'Installing graphics compatibility and compute packages: {packages}')
			install_session.add_additional_packages(packages)

		if config.install_opencl and driver in (GfxDriver.AllOpenSource, GfxDriver.AmdOpenSource, GfxDriver.NvidiaOpenSource):
			drivers = {
				GfxDriver.AllOpenSource: 'radeonsi,iris,nouveau',
				GfxDriver.AmdOpenSource: 'radeonsi',
				GfxDriver.NvidiaOpenSource: 'nouveau',
			}[driver]
			config_path = install_session.target / 'etc/environment.d/90-opencl.conf'
			config_path.parent.mkdir(parents=True, exist_ok=True)
			config_path.write_text(f'# Enable Mesa Rusticl for the selected graphics driver.\nRUSTICL_ENABLE={drivers}\n')

	def _multilib_packages(self, driver: GfxDriver) -> list[str]:
		match driver:
			case GfxDriver.AllOpenSource:
				return ['lib32-mesa', 'lib32-vulkan-radeon', 'lib32-vulkan-intel', 'lib32-vulkan-nouveau', 'lib32-vulkan-icd-loader']
			case GfxDriver.AmdOpenSource:
				return ['lib32-mesa', 'lib32-vulkan-radeon', 'lib32-vulkan-icd-loader']
			case GfxDriver.IntelOpenSource:
				return ['lib32-mesa', 'lib32-vulkan-intel', 'lib32-vulkan-icd-loader']
			case GfxDriver.NvidiaOpenKernel:
				return ['lib32-nvidia-utils', 'lib32-vulkan-icd-loader']
			case GfxDriver.NvidiaOpenSource:
				return ['lib32-mesa', 'lib32-vulkan-nouveau', 'lib32-vulkan-icd-loader']
			case GfxDriver.VMOpenSource:
				return ['lib32-mesa']

	def _opencl_packages(self, driver: GfxDriver, multilib: bool) -> list[str]:
		match driver:
			case GfxDriver.AllOpenSource | GfxDriver.AmdOpenSource | GfxDriver.NvidiaOpenSource:
				packages = ['opencl-mesa', 'ocl-icd', 'clinfo']
				if multilib:
					packages.append('lib32-opencl-mesa')
				return packages
			case GfxDriver.IntelOpenSource:
				return ['intel-compute-runtime', 'ocl-icd', 'clinfo']
			case GfxDriver.NvidiaOpenKernel:
				packages = ['opencl-nvidia', 'ocl-icd', 'clinfo']
				if multilib:
					packages.append('lib32-opencl-nvidia')
				return packages
			case GfxDriver.VMOpenSource:
				return []
