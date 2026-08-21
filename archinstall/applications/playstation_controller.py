from typing import TYPE_CHECKING

from archinstall.lib.log import debug
from archinstall.lib.models.gaming import GamingConfiguration

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


class PlayStationControllerApp:
	def install(self, install_session: Installer, config: GamingConfiguration) -> None:
		if not config.disable_playstation_touchpad:
			return

		debug('Disabling PlayStation controller touchpads as libinput mouse devices')
		rules = install_session.target / 'etc/udev/rules.d/72-playstation-controller-touchpads.rules'
		rules.parent.mkdir(parents=True, exist_ok=True)
		rules.write_text(
			'# Keep DualShock 4 and DualSense touchpads from controlling the desktop pointer.\n'
			'ATTRS{name}=="Sony Interactive Entertainment Wireless Controller Touchpad", ENV{LIBINPUT_IGNORE_DEVICE}="1"\n'
			'ATTRS{name}=="Wireless Controller Touchpad", ENV{LIBINPUT_IGNORE_DEVICE}="1"\n'
			'ATTRS{name}=="Sony Interactive Entertainment DualSense Wireless Controller Touchpad", ENV{LIBINPUT_IGNORE_DEVICE}="1"\n'
			'ATTRS{name}=="DualSense Wireless Controller Touchpad", ENV{LIBINPUT_IGNORE_DEVICE}="1"\n'
		)
