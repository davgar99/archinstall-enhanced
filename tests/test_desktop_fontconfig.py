from pathlib import Path

from archinstall.applications.fonts import (
	BITMAP_PRESET_TARGET,
	RENDERING_PRESET_NAME,
	configure_font_rendering,
)
from archinstall.default_profiles.desktop import DesktopProfile
from archinstall.default_profiles.desktops.sway import SwayProfile


class FakeInstaller:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.packages: list[str] = []
		self.services: list[str] = []

	def add_additional_packages(self, packages: list[str]) -> None:
		self.packages.extend(packages)

	def enable_service(self, service: str) -> None:
		self.services.append(service)


def test_desktop_enables_fontconfig_preset_without_adding_font_families(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	profile = DesktopProfile()

	profile.install(installer)  # type: ignore[arg-type]
	profile.post_install(installer)  # type: ignore[arg-type]

	assert 'fontconfig' in installer.packages
	assert 'pacman-contrib' in installer.packages
	assert 'xdg-desktop-portal-gtk' in installer.packages
	assert not any(package.startswith(('noto-fonts', 'ttf-')) for package in installer.packages)
	assert installer.services == ['paccache.timer']

	fontconfig_link = tmp_path / 'etc/fonts/conf.d/70-no-bitmaps-except-emoji.conf'
	assert fontconfig_link.is_symlink()
	assert fontconfig_link.readlink() == BITMAP_PRESET_TARGET

	rendering_config = (tmp_path / 'etc/fonts/conf.d' / RENDERING_PRESET_NAME).read_text(encoding='utf-8')
	assert '<edit name="antialias" mode="assign"><bool>true</bool></edit>' in rendering_config
	assert '<edit name="hinting" mode="assign"><bool>true</bool></edit>' in rendering_config
	assert '<edit name="hintstyle" mode="assign"><const>hintslight</const></edit>' in rendering_config
	assert '<edit name="lcdfilter" mode="assign"><const>lcddefault</const></edit>' in rendering_config
	assert 'rgba' not in rendering_config
	assert 'FREETYPE_PROPERTIES' not in rendering_config
	assert 'stem-darkening' not in rendering_config
	assert 'family' not in rendering_config


def test_font_rendering_configuration_is_idempotent_and_repairs_wrong_symlink(tmp_path: Path) -> None:
	conf_dir = tmp_path / 'etc/fonts/conf.d'
	conf_dir.mkdir(parents=True)
	bitmap_link = conf_dir / '70-no-bitmaps-except-emoji.conf'
	bitmap_link.symlink_to('/wrong/fontconfig/preset.conf')

	configure_font_rendering(tmp_path)
	configure_font_rendering(tmp_path)

	assert bitmap_link.is_symlink()
	assert bitmap_link.readlink() == BITMAP_PRESET_TARGET
	assert (conf_dir / RENDERING_PRESET_NAME).is_file()


def test_font_rendering_does_not_replace_existing_bitmap_configuration(tmp_path: Path) -> None:
	conf_dir = tmp_path / 'etc/fonts/conf.d'
	conf_dir.mkdir(parents=True)
	bitmap_config = conf_dir / '70-no-bitmaps-except-emoji.conf'
	bitmap_config.write_text('custom administrator configuration\n', encoding='utf-8')

	configure_font_rendering(tmp_path)

	assert bitmap_config.read_text(encoding='utf-8') == 'custom administrator configuration\n'


def test_font_rendering_replaces_managed_config_symlink_without_following_it(tmp_path: Path) -> None:
	conf_dir = tmp_path / 'etc/fonts/conf.d'
	conf_dir.mkdir(parents=True)
	outside = tmp_path / 'outside.conf'
	outside.write_text('must stay untouched\n', encoding='utf-8')
	rendering_config = conf_dir / RENDERING_PRESET_NAME
	rendering_config.symlink_to(outside)

	configure_font_rendering(tmp_path)

	assert not rendering_config.is_symlink()
	assert rendering_config.is_file()
	assert outside.read_text(encoding='utf-8') == 'must stay untouched\n'


def test_sway_includes_screen_sharing_portal() -> None:
	assert 'xdg-desktop-portal-wlr' in SwayProfile().packages
