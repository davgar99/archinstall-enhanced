from pathlib import Path
from unittest.mock import MagicMock

from archinstall.lib.args import ArchConfig, ArchConfigType, Arguments
from archinstall.lib.installer import Installer
from archinstall.lib.models.application import ZramAlgorithm, ZramConfiguration


def test_zram_configuration_roundtrip() -> None:
	config = ZramConfiguration(
		enabled=True,
		algorithm=ZramAlgorithm.ZSTD,
		swappiness_tweaks=True,
	)
	serialized = config.json()

	assert serialized == {
		'enabled': True,
		'algorithm': 'zstd',
		'swappiness_tweaks': True,
	}
	assert ZramConfiguration.parse_arg(serialized) == config

	arch_config = ArchConfig(swap=config)
	assert arch_config.safe_config()[ArchConfigType.SWAP] == serialized
	assert ArchConfig.from_config({'swap': serialized}, Arguments()).swap == config


def test_zram_configuration_parses_legacy_config() -> None:
	config_bool = ZramConfiguration.parse_arg(True)
	assert config_bool == ZramConfiguration(enabled=True, algorithm=ZramAlgorithm.ZSTD, swappiness_tweaks=False)

	config_dict = ZramConfiguration.parse_arg({'enabled': True, 'algorithm': 'lz4'})
	assert config_dict == ZramConfiguration(enabled=True, algorithm=ZramAlgorithm.LZ4, swappiness_tweaks=False)

	balanced_config = ZramConfiguration.parse_arg({'enabled': True, 'algorithm': 'lzo-rle zstd(level=3) (type=idle)'})
	assert balanced_config == ZramConfiguration(enabled=True, algorithm=ZramAlgorithm.ZSTD, swappiness_tweaks=False)


def test_zram_configuration_summary() -> None:
	config_disabled = ZramConfiguration(enabled=False)
	assert 'Disabled' in config_disabled.summary()[0]

	config_enabled = ZramConfiguration(enabled=True, algorithm=ZramAlgorithm.ZSTD, swappiness_tweaks=True)
	summary = config_enabled.summary()
	assert len(summary) == 3
	assert 'zstd' in summary[1]
	assert 'Enabled' in summary[2]


def test_setup_swap_with_swappiness_tweaks(tmp_path: Path) -> None:
	installer = MagicMock(spec=Installer)
	installer.target = tmp_path
	installer.pacman = MagicMock()

	Installer.setup_swap(
		installer,
		algo=ZramAlgorithm.ZSTD,
		swappiness_tweaks=True,
	)

	installer.pacman.strap.assert_called_once_with('zram-generator')
	installer.enable_service.assert_not_called()

	zram_conf = tmp_path / 'etc/systemd/zram-generator.conf'
	assert zram_conf.read_text() == '[zram0]\ncompression-algorithm = zstd(level=3)\n'

	sysctl_conf = tmp_path / 'etc/sysctl.d/99-vm-zram-parameters.conf'
	assert sysctl_conf.exists()
	assert sysctl_conf.read_text() == 'vm.swappiness = 180\nvm.watermark_boost_factor = 0\nvm.watermark_scale_factor = 125\nvm.page-cluster = 0\n'


def test_setup_swap_without_swappiness_tweaks(tmp_path: Path) -> None:
	installer = MagicMock(spec=Installer)
	installer.target = tmp_path
	installer.pacman = MagicMock()
	sysctl_conf = tmp_path / 'etc/sysctl.d/99-vm-zram-parameters.conf'
	sysctl_conf.parent.mkdir(parents=True)
	sysctl_conf.write_text('vm.swappiness = 180\n')

	Installer.setup_swap(
		installer,
		algo=ZramAlgorithm.LZ4,
		swappiness_tweaks=False,
	)

	zram_conf = tmp_path / 'etc/systemd/zram-generator.conf'
	assert zram_conf.read_text() == '[zram0]\ncompression-algorithm = lz4\n'

	assert not sysctl_conf.exists()
