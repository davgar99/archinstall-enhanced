import asyncio

from archinstall.lib.models.network import WifiNetwork
from archinstall.lib.network.wifi_handler import WifiHandler, WpaCliResult
from archinstall.tui.presentation import ActivityReporter

SCAN = 'bssid / frequency / signal level / flags / ssid\naa:bb:cc:dd:ee:ff\t2412\t-50\t[WPA2-PSK-CCMP][ESS]\tHome'


def test_scan_waits_for_delayed_results() -> None:
	handler = WifiHandler(scan_timeout=1, poll_interval=0)
	results = [[], WifiNetwork.from_wpa(SCAN)]
	handler._get_scan_results = lambda iface: results.pop(0)  # type: ignore[method-assign]

	assert asyncio.run(handler._wait_for_scan_results('wlan0'))[0].ssid == 'Home'


def test_scan_times_out() -> None:
	handler = WifiHandler(scan_timeout=0, poll_interval=0)
	handler._get_scan_results = lambda iface: []  # type: ignore[method-assign]

	assert asyncio.run(handler._wait_for_scan_results('wlan0')) == []
	assert handler._last_error is not None
	assert 'timed out' in handler._last_error


def test_connection_waits_for_matching_completed_state() -> None:
	handler = WifiHandler(connection_timeout=1, poll_interval=0)
	responses = [
		WpaCliResult(True, 'wpa_state=SCANNING\n'),
		WpaCliResult(True, 'wpa_state=COMPLETED\nssid=Home\n'),
	]
	handler._wpa_cli = lambda command, iface=None: responses.pop(0)  # type: ignore[method-assign]

	assert asyncio.run(handler._wait_for_connection('wlan0', 'Home')) is True


def test_connection_preserves_command_failure() -> None:
	handler = WifiHandler(connection_timeout=1, poll_interval=0)
	handler._wpa_cli = lambda command, iface=None: WpaCliResult(False, error='permission denied')  # type: ignore[method-assign]

	assert asyncio.run(handler._wait_for_connection('wlan0', 'Home')) is False
	assert handler._last_error == 'permission denied'


def test_connection_timeout_and_cancellation() -> None:
	handler = WifiHandler(connection_timeout=0, poll_interval=0)
	handler._wpa_cli = lambda command, iface=None: WpaCliResult(True, 'wpa_state=SCANNING\n')  # type: ignore[method-assign]
	assert asyncio.run(handler._wait_for_connection('wlan0', 'Home')) is False

	async def cancel_poll() -> None:
		waiting = WifiHandler(connection_timeout=30, poll_interval=1)
		waiting._wpa_cli = lambda command, iface=None: WpaCliResult(True, 'wpa_state=SCANNING\n')  # type: ignore[method-assign]
		task = asyncio.create_task(waiting._wait_for_connection('wlan0', 'Home'))
		await asyncio.sleep(0)
		task.cancel()
		try:
			await task
		except asyncio.CancelledError:
			return
		raise AssertionError('cancelled Wi-Fi polling task completed normally')

	asyncio.run(cancel_poll())


def test_activity_cancellation_stops_polling() -> None:
	handler = WifiHandler(connection_timeout=30, poll_interval=0)
	reporter = ActivityReporter('Connecting', cancellable=True)
	reporter.start()
	assert reporter.cancel()

	assert asyncio.run(handler._wait_for_connection('wlan0', 'Home', reporter)) is False


def test_network_id_zero_is_valid() -> None:
	handler = WifiHandler()
	handler._wpa_cli = lambda command, iface=None: WpaCliResult(  # type: ignore[method-assign]
		True,
		'network id / ssid / bssid / flags\n0\tHome\tany\t[CURRENT]\n',
	)
	assert handler._find_network_id('Home', 'wlan0') == 0
