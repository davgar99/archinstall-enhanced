import fcntl
import secrets
import select
import socket
import time
from typing import Any, Self, override

import pytest

import archinstall.lib.networking as networking


class FakeResponse:
	def __init__(self, data: bytes = b'ok') -> None:
		self.data = data
		self.closed = False

	def __enter__(self) -> Self:
		return self

	def __exit__(self, *_args: object) -> None:
		self.closed = True

	def read(self) -> bytes:
		return self.data


class FakeSocket:
	def __init__(self, response: bytes | None = None) -> None:
		self.response = response
		self.closed = False
		self.sent: list[tuple[bytes, tuple[str, int]]] = []

	def __enter__(self) -> Self:
		return self

	def __exit__(self, *_args: object) -> None:
		self.closed = True

	def fileno(self) -> int:
		return 7

	def sendto(self, data: bytes, address: tuple[str, int]) -> None:
		self.sent.append((data, address))

	def recvfrom(self, _size: int) -> tuple[bytes, tuple[str, int]]:
		assert self.response is not None
		return self.response, ('127.0.0.1', 0)


class FakeEpoll:
	def __init__(self) -> None:
		self.closed = False
		self.poll_calls = 0
		self.registered: list[tuple[Any, int]] = []

	def register(self, target: object, flags: int) -> None:
		self.registered.append((target, flags))

	def poll(self, _timeout: float) -> list[tuple[int, int]]:
		self.poll_calls += 1
		return [(7, select.EPOLLIN)] if self.poll_calls == 1 else []

	def close(self) -> None:
		self.closed = True


def test_fetch_data_merges_existing_query_and_preserves_fragment(monkeypatch: pytest.MonkeyPatch) -> None:
	response = FakeResponse(b'payload')
	requested_urls: list[str] = []

	def open_url(url: str, **_kwargs: object) -> FakeResponse:
		requested_urls.append(url)
		return response

	monkeypatch.setattr(networking, 'urlopen', open_url)

	data = networking.fetch_data_from_url(
		'https://example.com/api?existing=1#section',
		{'new': 'two words'},
	)

	assert data == b'payload'
	assert requested_urls == ['https://example.com/api?existing=1&new=two+words#section']
	assert response.closed


def test_get_hw_addr_closes_socket(monkeypatch: pytest.MonkeyPatch) -> None:
	fake_socket = FakeSocket()
	mac = bytes.fromhex('001122334455')
	ioctl_response = b'\x00' * 18 + mac + b'\x00' * 8

	monkeypatch.setattr(socket, 'socket', lambda *_args: fake_socket)
	monkeypatch.setattr(fcntl, 'ioctl', lambda *_args: ioctl_response)

	assert networking.get_hw_addr('eth0') == '00:11:22:33:44:55'
	assert fake_socket.closed


def test_calc_checksum_folds_repeated_carry() -> None:
	packet = bytes.fromhex('a513fc27e12fabe9d1ac')
	assert networking.calc_checksum(packet) == 0xFFFD


def test_ping_handles_ipv4_options_and_closes_resources(monkeypatch: pytest.MonkeyPatch) -> None:
	identifier = b'archinstall-1000'
	# IPv4 version 4 with IHL=6 means a 24-byte IP header. The ICMP type is
	# therefore byte 24 rather than the common fixed offset of 20.
	response = bytes([0x46]) + b'\x00' * 23 + b'\x00' + b'\x00' * 7 + identifier
	fake_socket = FakeSocket(response)
	watchdog = FakeEpoll()
	times = iter([0.0, 0.01, 0.02])

	monkeypatch.setattr(secrets, 'randbelow', lambda _limit: 0)
	monkeypatch.setattr(socket, 'socket', lambda *_args: fake_socket)
	monkeypatch.setattr(select, 'epoll', lambda: watchdog)
	monkeypatch.setattr(time, 'monotonic', lambda: next(times))

	assert networking.ping('example.com', timeout=1) == 20
	assert fake_socket.closed
	assert watchdog.closed


def test_ping_closes_resources_when_send_fails(monkeypatch: pytest.MonkeyPatch) -> None:
	class FailingSocket(FakeSocket):
		@override
		def sendto(self, data: bytes, address: tuple[str, int]) -> None:
			raise OSError('send failed')

	fake_socket = FailingSocket()
	watchdog = FakeEpoll()

	monkeypatch.setattr(socket, 'socket', lambda *_args: fake_socket)
	monkeypatch.setattr(select, 'epoll', lambda: watchdog)

	with pytest.raises(OSError, match='send failed'):
		networking.ping('example.com', timeout=1)

	assert fake_socket.closed
	assert watchdog.closed
