from pathlib import Path
from unittest.mock import MagicMock

import pytest

from archinstall.lib.args import ArchConfig, ArchConfigType, Arguments
from archinstall.lib.installer import Installer
from archinstall.lib.models.application import ZramAlgorithm, ZramConfiguration
from archinstall.tui.menu_item import MenuItemGroup


def test_zram_configuration_roundtrip() -> None:
	config = ZramConfiguration(
		enabled=True,
		algorithm=ZramAlgorithm.ZSTD,
	)
	serialized = config.json()

	assert serialized == {
		'enabled': True,
		'algorithm': 'zstd',
	}
	assert ZramConfiguration.parse_arg(serialized) == config

	arch_config = ArchConfig(swap=config)
	assert arch_config.safe_config()[ArchConfigType.SWAP] == serialized
	assert ArchConfig.from_config({'swap': serialized}, Arguments()).swap == config


def test_zram_configuration_parses_legacy_config() -> None:
	config_bool = ZramConfiguration.parse_arg(True)
	assert config_bool == ZramConfiguration(enabled=True, algorithm=ZramAlgorithm.ZSTD)

	config_dict = ZramConfiguration.parse_arg({'enabled': True, 'algorithm': 'lz4'})
	assert config_dict == ZramConfiguration(enabled=True, algorithm=ZramAlgorithm.LZ4)

	balanced_config = ZramConfiguration.parse_arg({'enabled': True, 'algorithm': 'lzo-rle zstd(level=3) (type=idle)', 'swappiness_tweaks': False})
	assert balanced_config == ZramConfiguration(enabled=True, algorithm=ZramAlgorithm.ZSTD)


def test_zram_configuration_summary() -> None:
	config_disabled = ZramConfiguration(enabled=False)
	assert 'Disabled' in config_disabled.summary()[0]

	config_enabled = ZramConfiguration(enabled=True, algorithm=ZramAlgorithm.ZSTD)
	summary = config_enabled.summary()
	assert len(summary) == 2
	assert summary[1] == 'Zram algorithm: zstd'


@pytest.mark.parametrize(
	('algorithm', 'generator_value'),
	[
		(ZramAlgorithm.ZSTD, 'zstd(level=3)'),
		(ZramAlgorithm.LZO_RLE, 'lzo-rle'),
		(ZramAlgorithm.LZO, 'lzo'),
		(ZramAlgorithm.LZ4, 'lz4(level=1)'),
		(ZramAlgorithm.LZ4HC, 'lz4hc(level=9)'),
		(ZramAlgorithm.IBM_842, '842'),
	],
)
def test_zram_generator_algorithm_profiles(algorithm: ZramAlgorithm, generator_value: str) -> None:
	assert algorithm.generator_value() == generator_value


def test_zram_menu_shows_only_algorithm_names() -> None:
	group = MenuItemGroup.from_enum(ZramAlgorithm, sort_items=False)

	assert [item.text for item in group.items] == ['zstd', 'lzo-rle', 'lzo', 'lz4', 'lz4hc', '842']


def test_setup_swap_uses_generator_defaults_and_archwiki_vm_settings(tmp_path: Path) -> None:
	installer = MagicMock(spec=Installer)
	installer.target = tmp_path
	installer.pacman = MagicMock()

	Installer.setup_swap(
		installer,
		algo=ZramAlgorithm.ZSTD,
	)

	installer.pacman.strap.assert_called_once_with('zram-generator')
	installer.enable_service.assert_not_called()

	zram_conf = tmp_path / 'etc/systemd/zram-generator.conf'
	assert zram_conf.read_text() == '[zram0]\nzram-size = min(ram, 8192)\ncompression-algorithm = zstd(level=3)\n'

	sysctl_conf = tmp_path / 'etc/sysctl.d/99-vm-zram-parameters.conf'
	assert sysctl_conf.exists()
	assert sysctl_conf.read_text() == 'vm.swappiness = 180\nvm.watermark_boost_factor = 0\nvm.watermark_scale_factor = 125\nvm.page-cluster = 0\n'


def test_setup_swap_uses_selected_kernel_default_compressor(tmp_path: Path) -> None:
	installer = MagicMock(spec=Installer)
	installer.target = tmp_path
	installer.pacman = MagicMock()
	sysctl_conf = tmp_path / 'etc/sysctl.d/99-vm-zram-parameters.conf'
	sysctl_conf.parent.mkdir(parents=True)
	sysctl_conf.write_text('vm.swappiness = 180\n')

	Installer.setup_swap(
		installer,
		algo=ZramAlgorithm.LZ4,
	)

	zram_conf = tmp_path / 'etc/systemd/zram-generator.conf'
	assert zram_conf.read_text() == '[zram0]\nzram-size = min(ram, 8192)\ncompression-algorithm = lz4(level=1)\n'

	assert sysctl_conf.read_text() == 'vm.swappiness = 180\nvm.watermark_boost_factor = 0\nvm.watermark_scale_factor = 125\nvm.page-cluster = 0\n'
