import inspect
from pathlib import Path

import pytest

from archinstall.applications.fonts import (
	BITMAP_PRESET_NAME,
	BITMAP_PRESET_TARGET,
	enable_no_bitmaps_except_emoji,
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

	fontconfig_link = tmp_path / 'etc/fonts/conf.d' / BITMAP_PRESET_NAME
	assert fontconfig_link.is_symlink()
	assert fontconfig_link.readlink() == BITMAP_PRESET_TARGET


def test_fontconfig_preset_configuration_is_idempotent(tmp_path: Path) -> None:
	enable_no_bitmaps_except_emoji(tmp_path)
	fontconfig_link = tmp_path / 'etc/fonts/conf.d' / BITMAP_PRESET_NAME
	inode = fontconfig_link.lstat().st_ino

	enable_no_bitmaps_except_emoji(tmp_path)

	assert fontconfig_link.is_symlink()
	assert fontconfig_link.readlink() == BITMAP_PRESET_TARGET
	assert fontconfig_link.lstat().st_ino == inode


def test_fontconfig_preset_repairs_incorrect_symlink(tmp_path: Path) -> None:
	conf_dir = tmp_path / 'etc/fonts/conf.d'
	conf_dir.mkdir(parents=True)
	fontconfig_link = conf_dir / BITMAP_PRESET_NAME
	fontconfig_link.symlink_to('/wrong/fontconfig/preset.conf')

	enable_no_bitmaps_except_emoji(tmp_path)

	assert fontconfig_link.is_symlink()
	assert fontconfig_link.readlink() == BITMAP_PRESET_TARGET


def test_fontconfig_preset_preserves_administrator_regular_file(tmp_path: Path) -> None:
	conf_dir = tmp_path / 'etc/fonts/conf.d'
	conf_dir.mkdir(parents=True)
	fontconfig_config = conf_dir / BITMAP_PRESET_NAME
	fontconfig_config.write_text('custom administrator configuration\n', encoding='utf-8')
	inode = fontconfig_config.stat().st_ino

	enable_no_bitmaps_except_emoji(tmp_path)

	assert fontconfig_config.read_text(encoding='utf-8') == 'custom administrator configuration\n'
	assert fontconfig_config.stat().st_ino == inode


def test_fontconfig_preset_rejects_unexpected_filesystem_object(tmp_path: Path) -> None:
	conf_dir = tmp_path / 'etc/fonts/conf.d'
	conf_dir.mkdir(parents=True)
	unexpected_path = conf_dir / BITMAP_PRESET_NAME
	unexpected_path.mkdir()

	with pytest.raises(ValueError, match='not a regular file or symlink'):
		enable_no_bitmaps_except_emoji(tmp_path)


def test_fontconfig_preset_does_not_generate_redundant_rendering_defaults(tmp_path: Path) -> None:
	enable_no_bitmaps_except_emoji(tmp_path)
	conf_dir = tmp_path / 'etc/fonts/conf.d'

	assert not (conf_dir / '45-archinstall-enhanced-rendering.conf').exists()
	assert not (conf_dir / '45-font-rendering-defaults.conf').exists()
	assert sorted(path.name for path in conf_dir.iterdir()) == [BITMAP_PRESET_NAME]

	source = inspect.getsource(enable_no_bitmaps_except_emoji) + inspect.getsource(DesktopProfile.post_install)
	for forbidden in (
		'antialias',
		'hinting',
		'hintstyle',
		'lcdfilter',
		'rgba',
		'family',
		'.Xresources',
		'FREETYPE_PROPERTIES',
		'interpreter-version',
		'stem-darkening',
		'embeddedbitmap',
		'fc-cache',
	):
		assert forbidden not in source


def test_sway_includes_screen_sharing_portal() -> None:
	assert 'xdg-desktop-portal-wlr' in SwayProfile().packages
