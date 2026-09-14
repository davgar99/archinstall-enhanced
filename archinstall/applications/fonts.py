from pathlib import Path
from typing import TYPE_CHECKING

from archinstall.lib.log import debug
from archinstall.lib.models.application import FontsConfiguration

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


BITMAP_PRESET_NAME = '70-no-bitmaps-except-emoji.conf'
BITMAP_PRESET_TARGET = Path('/usr/share/fontconfig/conf.avail') / BITMAP_PRESET_NAME
RENDERING_PRESET_NAME = '45-archinstall-enhanced-rendering.conf'
RENDERING_PRESET = '''<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <match target="font">
    <edit name="antialias" mode="assign"><bool>true</bool></edit>
    <edit name="hinting" mode="assign"><bool>true</bool></edit>
    <edit name="hintstyle" mode="assign"><const>hintslight</const></edit>
    <edit name="lcdfilter" mode="assign"><const>lcddefault</const></edit>
  </match>
</fontconfig>
'''


def configure_font_rendering(target: Path) -> None:
	"""Install conservative system-wide Fontconfig defaults for desktop sessions."""
	conf_dir = target / 'etc/fonts/conf.d'
	conf_dir.mkdir(parents=True, exist_ok=True)

	bitmap_link = conf_dir / BITMAP_PRESET_NAME
	if bitmap_link.is_symlink():
		if bitmap_link.readlink() != BITMAP_PRESET_TARGET:
			bitmap_link.unlink()
			bitmap_link.symlink_to(BITMAP_PRESET_TARGET)
	elif not bitmap_link.exists():
		bitmap_link.symlink_to(BITMAP_PRESET_TARGET)

	rendering_config = conf_dir / RENDERING_PRESET_NAME
	if rendering_config.is_symlink():
		rendering_config.unlink()
	elif rendering_config.exists() and not rendering_config.is_file():
		raise ValueError(f'Font rendering configuration path is not a regular file: {rendering_config}')

	rendering_config.write_text(RENDERING_PRESET, encoding='utf-8')


class FontsApp:
	def install(self, install_session: Installer, fonts_config: FontsConfiguration) -> None:
		packages = [f.value for f in fonts_config.fonts]
		debug(f'Installing fonts: {packages}')
		install_session.add_additional_packages(packages)
