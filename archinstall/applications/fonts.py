from pathlib import Path
from typing import TYPE_CHECKING

from archinstall.lib.log import debug
from archinstall.lib.models.application import FontsConfiguration

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


BITMAP_PRESET_NAME = '70-no-bitmaps-except-emoji.conf'
BITMAP_PRESET_TARGET = Path('/usr/share/fontconfig/conf.avail') / BITMAP_PRESET_NAME


def enable_no_bitmaps_except_emoji(target: Path) -> None:
	"""Enable Arch's packaged Fontconfig bitmap policy without overriding administrator files."""
	conf_dir = target / 'etc/fonts/conf.d'
	conf_dir.mkdir(parents=True, exist_ok=True)

	preset_link = conf_dir / BITMAP_PRESET_NAME
	if preset_link.is_symlink():
		if preset_link.readlink() == BITMAP_PRESET_TARGET:
			return
		preset_link.unlink()
	elif preset_link.exists():
		if preset_link.is_file():
			return
		raise ValueError(f'Fontconfig preset path is not a regular file or symlink: {preset_link}')

	preset_link.symlink_to(BITMAP_PRESET_TARGET)


class FontsApp:
	def install(self, install_session: Installer, fonts_config: FontsConfiguration) -> None:
		packages = [f.value for f in fonts_config.fonts]
		debug(f'Installing fonts: {packages}')
		install_session.add_additional_packages(packages)
