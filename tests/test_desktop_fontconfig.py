from pathlib import Path

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
	assert fontconfig_link.readlink() == Path('/usr/share/fontconfig/conf.avail/70-no-bitmaps-except-emoji.conf')


def test_sway_includes_screen_sharing_portal() -> None:
	assert 'xdg-desktop-portal-wlr' in SwayProfile().packages
