from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self

import pytest

from archinstall.lib.models.device import DiskLayoutType
from archinstall.scripts import guided
from archinstall.tui.presentation import ActivityReporter


class _FakeInstaller:
	def __init__(self, events: list[str], failure: BaseException | None = None) -> None:
		self.events = events
		self.failure = failure

	def __enter__(self) -> Self:
		self.events.append('enter')
		return self

	def __exit__(self, *args: object) -> None:
		self.events.append('cleanup')

	def sanity_check(self, *args: Any) -> None:
		self.events.append('sanity')

	def minimal_installation(self, **kwargs: Any) -> None:
		self.events.append('base')
		if self.failure:
			raise self.failure

	def genfstab(self) -> None:
		self.events.append('fstab')


def _handlers(tmp_path: Path) -> tuple[Any, ...]:
	disk = SimpleNamespace(
		mountpoint=tmp_path / 'target',
		config_type=DiskLayoutType.Pre_mount,
		disk_encryption=None,
		has_default_btrfs_vols=lambda: False,
	)
	config = SimpleNamespace(
		disk_config=disk,
		kernels=['linux'],
		mirror_config=None,
		gaming_config=None,
		bootloader_config=None,
		locale_config=None,
		hostname='archlinux',
		pacman_config=None,
		swap=None,
		network_config=None,
		auth_config=None,
		app_config=None,
		profile_config=None,
		packages=[],
		timezone=None,
		hardware_clock_utc=False,
		ntp=False,
		services=[],
		custom_commands=[],
	)
	args = SimpleNamespace(mountpoint=tmp_path / 'target', silent=True, offline=False, skip_ntp=True, skip_wkd=True)
	return SimpleNamespace(config=config, args=args), SimpleNamespace(), SimpleNamespace(), SimpleNamespace(), SimpleNamespace()


def _patch_optional_collaborators(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(guided, 'accessibility_tools_in_use', lambda: False)
	monkeypatch.setattr('archinstall.scripts.guided.VirtualBoxGuestApp.detected', lambda: False)
	monkeypatch.setattr(guided, 'disk_layouts', lambda: 'fake layout')
	monkeypatch.setattr('archinstall.scripts.guided.GraphicsExtrasApp.install', lambda *args: None)
	monkeypatch.setattr('archinstall.scripts.guided.FilesystemHandler.perform_filesystem_operations', lambda *args: None)


def test_installation_stages_cleanup_and_outcome(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	events: list[str] = []
	fake = _FakeInstaller(events)
	monkeypatch.setattr(guided, 'Installer', lambda *args, **kwargs: fake)
	_patch_optional_collaborators(monkeypatch)
	reporter = ActivityReporter('Installing')

	config, mirrors, auth, applications, gaming = _handlers(tmp_path)
	session = guided._perform_installation_core(config, mirrors, auth, applications, gaming, reporter)
	state = reporter.snapshot()

	assert events == ['enter', 'sanity', 'base', 'fstab', 'cleanup']
	assert state.completed_steps == state.total_steps == 10
	assert state.label == 'Final validation and log sync'
	assert session.outcome.target_mountpoint == tmp_path / 'target'
	assert session.installation is fake  # type: ignore[comparison-overlap]


def test_installation_failure_keeps_stage_and_exception_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	events: list[str] = []
	error = RuntimeError('pacstrap failed')
	fake = _FakeInstaller(events, error)
	monkeypatch.setattr(guided, 'Installer', lambda *args, **kwargs: fake)
	_patch_optional_collaborators(monkeypatch)
	config, mirrors, auth, applications, gaming = _handlers(tmp_path)

	with pytest.raises(RuntimeError) as raised:
		guided._perform_installation_core(config, mirrors, auth, applications, gaming, ActivityReporter('Installing'))

	assert raised.value is error
	assert events[-1] == 'cleanup'
	assert any('Base installation' in note for note in getattr(error, '__notes__', []))
