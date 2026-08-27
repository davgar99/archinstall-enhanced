from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self, override

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


@pytest.mark.parametrize(
	('upgrade', 'expected'),
	[(None, 'Archinstall Enhanced'), ('4.5', 'Archinstall Enhanced (New version available: 4.5)')],
)
def test_guided_menu_uses_canonical_title(
	upgrade: str | None,
	expected: str,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	captured: dict[str, Any] = {}

	def global_menu(*args: Any, **kwargs: Any) -> object:
		captured.update(kwargs)
		return object()

	monkeypatch.setattr(guided, 'check_version_upgrade', lambda: upgrade)
	monkeypatch.setattr(guided, 'GlobalMenu', global_menu)
	monkeypatch.setattr('archinstall.scripts.guided.tui.run', lambda _menu: object())
	handler: Any = SimpleNamespace(config=object(), args=SimpleNamespace(skip_boot=False, advanced=False))
	mirrors: Any = SimpleNamespace()

	guided.show_menu(handler, mirrors)

	assert captured['title'] == expected


def test_installation_stage_labels_are_reported_in_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	class RecordingReporter(ActivityReporter):
		def __init__(self) -> None:
			super().__init__('Installing')
			self.stages: list[tuple[int, int, str]] = []

		@override
		def set_stage(self, label: str, completed_steps: int, total_steps: int) -> None:
			super().set_stage(label, completed_steps, total_steps)
			self.stages.append((completed_steps, total_steps, label))

	fake = _FakeInstaller([])
	monkeypatch.setattr(guided, 'Installer', lambda *args, **kwargs: fake)
	_patch_optional_collaborators(monkeypatch)
	reporter = RecordingReporter()

	config, mirrors, auth, applications, gaming = _handlers(tmp_path)
	guided._perform_installation_core(config, mirrors, auth, applications, gaming, reporter)

	assert reporter.stages == [
		(1, 10, 'Storage and mount validation'),
		(2, 10, 'Encryption and mirrors'),
		(3, 10, 'Base installation'),
		(4, 10, 'Bootloader'),
		(5, 10, 'Networking and accounts'),
		(6, 10, 'Applications and gaming'),
		(7, 10, 'Profiles and packages'),
		(8, 10, 'System settings'),
		(9, 10, 'Post-install hooks'),
		(10, 10, 'Final validation and log sync'),
	]


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


def test_interactive_installation_failure_returns_to_configuration_menu(monkeypatch: pytest.MonkeyPatch) -> None:
	class StopAfterRecovery(Exception):
		pass

	show_count = 0
	tui_results = iter((True, None))
	config = SimpleNamespace(
		disk_config=object(),
		bootloader_config=None,
		write_debug=lambda: None,
		save=lambda: None,
	)
	handler = SimpleNamespace(
		config=config,
		args=SimpleNamespace(silent=False, dry_run=False, offline=False, verbose=False),
	)

	def show_menu(*_args: object) -> None:
		nonlocal show_count
		show_count += 1
		if show_count == 2:
			raise StopAfterRecovery

	monkeypatch.setattr(guided, 'show_menu', show_menu)
	monkeypatch.setattr(guided, 'MirrorListHandler', lambda **_kwargs: SimpleNamespace())
	monkeypatch.setattr(guided, 'validate_bootloader_layout', lambda *_args: None)
	monkeypatch.setattr(guided, 'delayed_warning', lambda _message: True)
	monkeypatch.setattr(guided, 'perform_installation', lambda *_args: (_ for _ in ()).throw(RuntimeError('Installation worker failed')))
	monkeypatch.setattr('archinstall.scripts.guided.tui.run', lambda _screen: next(tui_results))

	with pytest.raises(StopAfterRecovery):
		guided.main(handler)  # type: ignore[arg-type]

	assert show_count == 2
