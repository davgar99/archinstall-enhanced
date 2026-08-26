from typing import TYPE_CHECKING

from archinstall.lib.log import debug
from archinstall.lib.models.application import MultimediaConfiguration

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


class MultimediaApp:
	@property
	def packages(self) -> list[str]:
		return [
			'gstreamer',
			'gst-plugins-base',
			'gst-plugins-good',
			'gst-plugins-bad',
			'gst-plugins-ugly',
			'gst-libav',
			'gst-plugin-va',
			'ffmpeg',
		]

	def install(self, install_session: Installer, multimedia_config: MultimediaConfiguration) -> None:
		if not multimedia_config.enabled:
			return

		debug(f'Installing multimedia codecs and hardware acceleration plugins: {self.packages}')
		install_session.add_additional_packages(self.packages)
