from pathlib import Path

from archinstall.applications.multimedia import MultimediaApp
from archinstall.lib.applications.application_menu import ApplicationMenu
from archinstall.lib.models.application import ApplicationConfiguration, MultimediaConfiguration


class FakeInstaller:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.packages: list[str] = []

	def add_additional_packages(self, packages: list[str]) -> None:
		self.packages.extend(packages)


def test_multimedia_install_adds_complete_gstreamer_stack(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	MultimediaApp().install(installer, MultimediaConfiguration(enabled=True))  # type: ignore[arg-type]

	assert installer.packages == [
		'gstreamer',
		'gst-plugins-base',
		'gst-plugins-good',
		'gst-plugins-bad',
		'gst-plugins-ugly',
		'gst-libav',
		'gst-plugin-va',
		'ffmpeg',
	]


def test_multimedia_disabled_does_not_install_packages(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	MultimediaApp().install(installer, MultimediaConfiguration(enabled=False))  # type: ignore[arg-type]

	assert installer.packages == []


def test_multimedia_configuration_roundtrip_and_summary() -> None:
	config = ApplicationConfiguration(multimedia_config=MultimediaConfiguration(enabled=True))

	assert config.json() == {'multimedia_config': {'enabled': True}}
	assert ApplicationConfiguration.parse_arg({'multimedia_config': {'enabled': True}}) == config
	assert config.summary() == ['Multimedia codecs: Enabled']


def test_multimedia_menu_is_available() -> None:
	item = ApplicationMenu()._item_group.find_by_key('multimedia_config')

	assert item.enabled
	assert item.text == 'Multimedia codecs'
