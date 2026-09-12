from archinstall.lib.command import SysCommandWorker


def _worker() -> SysCommandWorker:
	return SysCommandWorker(['/bin/true'])


def test_contains_advances_to_absolute_match_end() -> None:
	worker = _worker()
	try:
		worker._trace_log = b'first token second token'
		worker._trace_log_pos = 6

		assert b'token' in worker
		assert worker._trace_log_pos == 11
	finally:
		worker.exit_code = 0
		worker.__exit__(None, None, None)


def test_iteration_does_not_move_cursor_before_complete_line() -> None:
	worker = _worker()
	try:
		worker._trace_log = b'partial'

		assert list(worker) == []
		assert worker._trace_log_pos == 0
	finally:
		worker.exit_code = 0
		worker.__exit__(None, None, None)


def test_iteration_consumes_only_complete_lines() -> None:
	worker = _worker()
	try:
		worker._trace_log = b'one\ntwo\npartial'

		assert list(worker) == [b'one\n', b'two\n']
		assert worker._trace_log_pos == len(b'one\ntwo\n')
	finally:
		worker.exit_code = 0
		worker.__exit__(None, None, None)


def test_context_exit_closes_epoll_resource() -> None:
	worker = _worker()
	worker.exit_code = 0
	worker.__exit__(None, None, None)

	assert worker.poll_object.closed
