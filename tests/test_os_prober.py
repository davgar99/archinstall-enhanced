from pathlib import Path
from typing import Any, cast

from archinstall.lib.bootloader.os_prober import enable_os_prober_in_grub_config, prepare_grub_os_prober
from archinstall.lib.models.bootloader import Bootloader, BootloaderConfiguration


class FakePacman:
	def __init__(self) -> None:
		self.calls: list[list[str] | str] = []

	def strap(self, packages: list[str] | str) -> None:
		self.calls.append(packages)


class FakeInstallation:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.pacman = FakePacman()


def test_enable_os_prober_replaces_and_deduplicates_setting() -> None:
	config = '#GRUB_DISABLE_OS_PROBER=true\nGRUB_TIMEOUT=5\nGRUB_DISABLE_OS_PROBER=true\n'

	updated = enable_os_prober_in_grub_config(config)

	assert updated.count('GRUB_DISABLE_OS_PROBER=false') == 1
	assert 'GRUB_DISABLE_OS_PROBER=true' not in updated
	assert 'GRUB_TIMEOUT=5' in updated


def test_enable_os_prober_appends_setting_when_missing() -> None:
	updated = enable_os_prober_in_grub_config('GRUB_TIMEOUT=5')

	assert updated == 'GRUB_TIMEOUT=5\nGRUB_DISABLE_OS_PROBER=false\n'


def test_bootloader_config_round_trip_preserves_os_prober() -> None:
	config = BootloaderConfiguration(
		bootloader=Bootloader.Grub,
		uki=False,
		removable=False,
		os_prober=True,
	)

	parsed = BootloaderConfiguration.parse_arg(config.json(), skip_boot=False)

	assert parsed == config
	assert parsed.os_prober is True
	assert 'os-prober: Enabled' in parsed.summary()


def test_os_prober_defaults_to_disabled() -> None:
	config = BootloaderConfiguration.get_default(uefi=True)

	assert config.os_prober is False


def test_os_prober_support_is_grub_only() -> None:
	assert Bootloader.Grub.has_os_prober_support() is True
	assert Bootloader.Systemd.has_os_prober_support() is False
	assert Bootloader.Limine.has_os_prober_support() is False


def test_prepare_grub_os_prober_installs_packages_and_updates_config(tmp_path: Path) -> None:
	grub_default = tmp_path / 'etc/default/grub'
	grub_default.parent.mkdir(parents=True)
	grub_default.write_text('#GRUB_DISABLE_OS_PROBER=true\nGRUB_TIMEOUT=5\n')
	installation = FakeInstallation(tmp_path)

	prepare_grub_os_prober(cast(Any, installation), Bootloader.Grub, True)

	assert installation.pacman.calls == [['grub', 'os-prober', 'fuse3']]
	assert grub_default.read_text() == 'GRUB_DISABLE_OS_PROBER=false\nGRUB_TIMEOUT=5\n'


def test_prepare_grub_os_prober_is_noop_when_disabled(tmp_path: Path) -> None:
	installation = FakeInstallation(tmp_path)

	prepare_grub_os_prober(cast(Any, installation), Bootloader.Grub, False)

	assert installation.pacman.calls == []


def test_prepare_grub_os_prober_ignores_non_grub_bootloader(tmp_path: Path) -> None:
	installation = FakeInstallation(tmp_path)

	prepare_grub_os_prober(cast(Any, installation), Bootloader.Systemd, True)

	assert installation.pacman.calls == []
