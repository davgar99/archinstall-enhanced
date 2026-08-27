"""Activity reporting primitives shared by the installer and Textual UI."""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum, auto
from pathlib import Path
from typing import cast, override

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, LoadingIndicator, ProgressBar, Static


class ActivityStatus(Enum):
	PENDING = auto()
	RUNNING = auto()
	COMPLETED = auto()
	FAILED = auto()
	CANCELLED = auto()


@dataclass(frozen=True)
class ActivityState:
	label: str
	detail: str = ''
	completed_steps: int | None = None
	total_steps: int | None = None
	status: ActivityStatus = ActivityStatus.PENDING
	started_at: float | None = None
	finished_at: float | None = None
	error: BaseException | None = None
	cancellable: bool = False

	@property
	def elapsed(self) -> float:
		end = self.finished_at if self.finished_at is not None else time.monotonic()
		return max(0, end - (self.started_at or end))


class ActivityReporter:
	"""Thread-safe bridge between an operation and its activity screen."""

	def __init__(self, label: str, cancellable: bool = False) -> None:
		self._state = ActivityState(label=label, cancellable=cancellable)
		self._lock = threading.Lock()

	def snapshot(self) -> ActivityState:
		with self._lock:
			return replace(self._state)

	def start(self) -> None:
		with self._lock:
			self._state = replace(self._state, status=ActivityStatus.RUNNING, started_at=time.monotonic())

	def set_stage(self, label: str, completed_steps: int, total_steps: int) -> None:
		if total_steps < 1 or completed_steps < 0 or completed_steps > total_steps:
			raise ValueError('Invalid activity stage progress')
		with self._lock:
			self._state = replace(
				self._state,
				label=label,
				completed_steps=completed_steps,
				total_steps=total_steps,
				status=ActivityStatus.RUNNING,
				started_at=self._state.started_at or time.monotonic(),
			)

	def set_detail(self, message: str) -> None:
		with self._lock:
			self._state = replace(self._state, detail=message)

	def complete(self) -> None:
		with self._lock:
			self._state = replace(self._state, status=ActivityStatus.COMPLETED, finished_at=time.monotonic())

	def fail(self, error: BaseException) -> None:
		with self._lock:
			self._state = replace(self._state, status=ActivityStatus.FAILED, error=error, finished_at=time.monotonic())

	def cancel(self) -> bool:
		with self._lock:
			if not self._state.cancellable or self._state.status is not ActivityStatus.RUNNING:
				return False
			self._state = replace(self._state, status=ActivityStatus.CANCELLED, finished_at=time.monotonic())
			return True

	@property
	def cancellation_requested(self) -> bool:
		return self.snapshot().status is ActivityStatus.CANCELLED


class Activity[ValueT]:
	def __init__(self, label: str, operation: Callable[[ActivityReporter], ValueT], cancellable: bool = False) -> None:
		self.reporter = ActivityReporter(label, cancellable=cancellable)
		self.operation = operation

	async def show(self) -> ValueT:
		from archinstall.tui.components import ActivityScreen
		from archinstall.tui.result import ResultType

		result = await ActivityScreen(self.reporter, self.operation).run()
		if result.has_error():
			raise result.get_error()
		if result.type_ is ResultType.Skip:
			raise ActivityCancelled(self.reporter.snapshot().label)
		if result.type_ is ResultType.Selection and not result.has_data():
			return cast(ValueT, None)
		return result.get_value()


class ActivityCancelled(Exception):
	"""Raised when a cancellable activity is explicitly cancelled."""


@dataclass(frozen=True)
class InstallationOutcome:
	elapsed_time: float
	target_mountpoint: Path
	log_path: Path


class ActivityWidget(Static):
	"""Unframed activity content using the stock blue/black/white presentation."""

	CSS = """
	ActivityWidget {
		width: 80%;
		height: auto;
		background: transparent;
		padding: 1 2;
	}
	ActivityWidget .activity-label { color: white; text-style: bold; }
	ActivityWidget .activity-detail { color: white; }
	ActivityWidget .activity-elapsed { color: white; }
	ActivityWidget LoadingIndicator { height: auto; }
	"""

	def __init__(self, reporter: ActivityReporter) -> None:
		super().__init__()
		self.reporter = reporter

	@override
	def compose(self) -> ComposeResult:
		with Vertical():
			yield Label('', classes='activity-label', id='activity-label')
			yield LoadingIndicator(id='activity-spinner')
			yield ProgressBar(total=100, show_eta=False, id='activity-progress')
			yield Label('', classes='activity-detail', id='activity-detail')
			yield Label('', classes='activity-elapsed', id='activity-elapsed')

	def on_mount(self) -> None:
		self.set_interval(0.2, self.refresh_state)
		self.refresh_state()

	def refresh_state(self) -> None:
		state = self.reporter.snapshot()
		known = state.completed_steps is not None and state.total_steps is not None
		label = state.label
		if known:
			label += f' — Step {state.completed_steps} of {state.total_steps}'
		self.query_one('#activity-label', Label).update(label)
		self.query_one('#activity-detail', Label).update(state.detail)
		self.query_one('#activity-elapsed', Label).update(f'Elapsed: {state.elapsed:.1f}s')
		spinner = self.query_one('#activity-spinner', LoadingIndicator)
		progress = self.query_one('#activity-progress', ProgressBar)
		spinner.display = not known and state.status in {ActivityStatus.PENDING, ActivityStatus.RUNNING}
		progress.display = known
		if known:
			assert state.completed_steps is not None and state.total_steps is not None
			progress.update(progress=100 * state.completed_steps / state.total_steps)
