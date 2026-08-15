from pathlib import Path

from archinstall.lib.models.pacman import PacmanConfiguration
from archinstall.lib.pacman.config import configure_pacman_options
from archinstall.lib.pacman.pacman_menu import PacmanMenu


def test_pacman_configuration_roundtrip() -> None:
	config = PacmanConfiguration(parallel_downloads=8, color=False, ilove_candy=True)
	serialized = config.json()

	assert serialized == {
		'parallel_downloads': 8,
		'color': False,
		'ilove_candy': True,
	}
	assert PacmanConfiguration.parse_arg(serialized) == config


def test_pacman_configuration_parses_legacy_config() -> None:
	config = PacmanConfiguration.parse_arg({'parallel_downloads': 3, 'color': True})

	assert config == PacmanConfiguration(parallel_downloads=3, color=True, ilove_candy=False)


def test_pacman_menu_exposes_parallel_downloads_and_ilove_candy() -> None:
	menu = PacmanMenu(PacmanConfiguration())

	parallel = menu._item_group.find_by_key('parallel_downloads')
	candy = menu._item_group.find_by_key('ilove_candy')
	assert parallel.enabled
	assert candy.enabled


def test_configure_pacman_options_enables_ilove_candy(tmp_path: Path) -> None:
	path = tmp_path / 'pacman.conf'
	path.write_text('[options]\n#Color\n#ParallelDownloads = 5\n\n[core]\nInclude = /etc/pacman.d/mirrorlist\n')

	configure_pacman_options(path, PacmanConfiguration(parallel_downloads=10, color=True, ilove_candy=True))

	assert path.read_text() == '[options]\nColor\nParallelDownloads = 10\n\nILoveCandy\n[core]\nInclude = /etc/pacman.d/mirrorlist\n'


def test_configure_pacman_options_disables_ilove_candy(tmp_path: Path) -> None:
	path = tmp_path / 'pacman.conf'
	path.write_text('[options]\nILoveCandy\nColor\nParallelDownloads = 5\n')

	configure_pacman_options(path, PacmanConfiguration(ilove_candy=False))

	assert '#ILoveCandy' in path.read_text().splitlines()
