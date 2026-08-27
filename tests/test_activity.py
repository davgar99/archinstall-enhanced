import asyncio
from typing import Any, cast, override

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Label

from archinstall.tui.components import ActivityScreen
from archinstall.tui.presentation import Activity, ActivityReporter, ActivityStatus, ActivityWidget
from archinstall.tui.result import Result


def test_activity_lifecycle() -> None:
	reporter = ActivityReporter('Waiting')
	assert reporter.snapshot().status is ActivityStatus.PENDING

	reporter.start()
	reporter.set_detail('Downloading package database')
	reporter.set_stage('Packages', 2, 4)
	state = reporter.snapshot()
	assert state.status is ActivityStatus.RUNNING
	assert (state.completed_steps, state.total_steps) == (2, 4)
	assert state.detail == 'Downloading package database'

	reporter.complete()
	assert reporter.snapshot().status is ActivityStatus.COMPLETED


def test_activity_failure_retains_original_exception() -> None:
	error = RuntimeError('package operation failed')
	reporter = ActivityReporter('Packages')
	reporter.start()
	reporter.fail(error)

	state = reporter.snapshot()
	assert state.status is ActivityStatus.FAILED
	assert state.error is error
	assert state.finished_at is not None


def test_activity_screen_does_not_mark_a_failed_operation_complete() -> None:
	error = RuntimeError("command ['git'] failed")
	reporter = ActivityReporter('Applications')

	def fail(_reporter: ActivityReporter) -> None:
		raise error

	screen = ActivityScreen[None](reporter, fail)
	cast(Any, screen._execute).__wrapped__(screen)

	state = reporter.snapshot()
	assert state.status is ActivityStatus.FAILED
	assert state.error is error
	assert screen._failure is error


def test_activity_protects_non_cancellable_operation() -> None:
	reporter = ActivityReporter('Formatting', cancellable=False)
	reporter.start()
	assert reporter.cancel() is False
	assert reporter.snapshot().status is ActivityStatus.RUNNING


def test_activity_allows_explicit_cancellation() -> None:
	reporter = ActivityReporter('Scanning', cancellable=True)
	reporter.start()
	assert reporter.cancel() is True
	assert reporter.cancellation_requested


def test_activity_accepts_successful_none_result(monkeypatch: pytest.MonkeyPatch) -> None:
	async def run(_screen: ActivityScreen[None]) -> Result[None]:
		return Result.selection(None)

	monkeypatch.setattr(ActivityScreen, 'run', run)
	result = asyncio.run(Activity[None]('Loading mirror regions', lambda _reporter: None).show())
	assert result is None


def test_activity_renders_command_failures_as_literal_text() -> None:
	reporter = ActivityReporter('Applications [6/10]')
	reporter.start()
	reporter.set_detail("Command ['git', 'https://aur.archlinux.org/yay.git'] failed")

	class ActivityApp(App[None]):
		@override
		def compose(self) -> ComposeResult:
			yield ActivityWidget(reporter)

	async def run() -> None:
		async with ActivityApp().run_test() as pilot:
			await pilot.pause()
			widget = pilot.app.query_one(ActivityWidget)
			widget.refresh_state()
			assert pilot.app.query_one('#activity-label', Label)._render_markup is False
			assert pilot.app.query_one('#activity-detail', Label)._render_markup is False

	asyncio.run(run())


@pytest.mark.parametrize(('completed', 'total'), [(-1, 2), (3, 2), (0, 0)])
def test_activity_rejects_invented_or_invalid_progress(completed: int, total: int) -> None:
	with pytest.raises(ValueError):
		ActivityReporter('Invalid').set_stage('Invalid', completed, total)
