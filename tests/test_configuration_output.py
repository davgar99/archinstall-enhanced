import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from pytest import MonkeyPatch

from archinstall.lib.args import USER_CONFIG_FILE, USER_CREDS_FILE, ArchConfig, ArchConfigHandler, ArchConfigType
from archinstall.lib.configuration import _destructive_targets, confirm_config
from archinstall.lib.menu.helpers import Confirmation
from archinstall.lib.models.device import DeviceModification, DiskLayoutConfiguration, DiskLayoutType, SectorSize, Size, Unit
from archinstall.tui.result import Result


def test_user_config_roundtrip(
	monkeypatch: MonkeyPatch,
	config_fixture: Path,
) -> None:
	monkeypatch.setattr('sys.argv', ['archinstall', '--config', str(config_fixture)])

	handler = ArchConfigHandler()
	arch_config = handler.config

	# the version is retrieved dynamically from an installed archinstall package
	# as there is no version present in the test environment we'll set it manually
	arch_config.version = '3.0.2'

	test_out_dir = Path('/tmp/')
	test_out_file = test_out_dir / USER_CONFIG_FILE

	arch_config.save(test_out_dir)

	result = json.loads(test_out_file.read_text())
	expected = json.loads(config_fixture.read_text())

	# the parsed config will check if the given device exists otherwise
	# it will ignore the modification; as this test will run on various local systems
	# and the CI pipeline there's no good way specify a real device so we'll simply
	# copy the expected result to the actual result
	result['disk_config']['config_type'] = expected['disk_config']['config_type']
	result['disk_config']['device_modifications'] = expected['disk_config']['device_modifications']

	assert json.dumps(
		result['mirror_config'],
		sort_keys=True,
	) == json.dumps(
		expected['mirror_config'],
		sort_keys=True,
	)


def test_creds_roundtrip(
	monkeypatch: MonkeyPatch,
	creds_fixture: Path,
) -> None:
	monkeypatch.setattr('sys.argv', ['archinstall', '--creds', str(creds_fixture)])

	handler = ArchConfigHandler()
	arch_config = handler.config

	test_out_dir = Path('/tmp/')
	test_out_file = test_out_dir / USER_CREDS_FILE

	arch_config.save(test_out_dir, creds=True)

	result = json.loads(test_out_file.read_text())
	expected = json.loads(creds_fixture.read_text())

	assert sorted(result.items()) == sorted(expected.items())


def test_installation_summary_uses_risk_first_order(monkeypatch: MonkeyPatch) -> None:
	class SummaryConfig:
		def __init__(self, value: str) -> None:
			self.value = value

		def summary(self) -> list[str]:
			return [self.value]

	config = ArchConfig()
	monkeypatch.setattr(
		config,
		'plain_cfg',
		lambda: {
			ArchConfigType.TIMEZONE: 'UTC',
			ArchConfigType.HOSTNAME: 'workstation',
			ArchConfigType.KERNELS: ['linux'],
		},
	)
	monkeypatch.setattr(
		config,
		'sub_cfg',
		lambda: {
			ArchConfigType.LOCALE_CONFIG: cast(Any, SummaryConfig('en_US')),
			ArchConfigType.DISK_CONFIG: cast(Any, SummaryConfig('/dev/sda')),
			ArchConfigType.AUTH_CONFIG: cast(Any, SummaryConfig('admin')),
		},
	)

	summary = config.as_summary()
	assert summary.index('Disk configuration') < summary.index('Kernels')
	assert summary.index('Kernels') < summary.index('Authentication')
	assert summary.index('Authentication') < summary.index('Hostname')
	assert summary.index('Hostname') < summary.index('Locales')
	assert summary.index('Locales') < summary.index('Timezone')


def _wiped_disk_config() -> ArchConfig:
	device = SimpleNamespace(
		device_info=SimpleNamespace(
			path=Path('/dev/sda'),
			model='VBOX HARDDISK',
			total_size=Size(64, Unit.GiB, SectorSize.default()),
		)
	)
	modification = DeviceModification(device=cast(Any, device), wipe=True)
	return ArchConfig(
		disk_config=DiskLayoutConfiguration(
			config_type=DiskLayoutType.Default,
			device_modifications=[modification],
		)
	)


def test_destructive_targets_name_drive_model_size_and_scope() -> None:
	targets = _destructive_targets(_wiped_disk_config())
	assert targets == ['/dev/sda — VBOX HARDDISK — 64 GiB (entire drive)']


def test_confirmation_reviews_summary_then_requires_destructive_confirmation(monkeypatch: MonkeyPatch) -> None:
	config = _wiped_disk_config()
	confirmations: list[Confirmation] = []
	results: Iterator[Result[bool]] = iter((Result.true(), Result.true()))

	async def show(confirmation: Confirmation) -> Result[bool]:
		confirmations.append(confirmation)
		return next(results)

	monkeypatch.setattr(Confirmation, 'show', show)
	assert asyncio.run(confirm_config(config)) is True
	assert len(confirmations) == 2
	assert confirmations[0]._preset is False
	assert confirmations[0]._group.focus_item is not None
	assert confirmations[0]._group.focus_item.value is False
	assert 'WARNING: DATA WILL BE PERMANENTLY DELETED' in confirmations[1]._header
	assert '/dev/sda — VBOX HARDDISK — 64 GiB (entire drive)' in confirmations[1]._header
	assert confirmations[1]._preset is False


def test_destructive_confirmation_can_stop_installation(monkeypatch: MonkeyPatch) -> None:
	results: Iterator[Result[bool]] = iter((Result.true(), Result.false()))

	async def show(_confirmation: Confirmation) -> Result[bool]:
		return next(results)

	monkeypatch.setattr(Confirmation, 'show', show)
	assert asyncio.run(confirm_config(_wiped_disk_config())) is False
