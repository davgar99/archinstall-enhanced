from pathlib import Path
from typing import Self

import pytest

import archinstall.lib.authentication.authentication_handler as authentication_handler_module
from archinstall.lib.authentication.authentication_handler import AuthenticationHandler
from archinstall.lib.models.authentication import U2FLoginConfiguration, U2FLoginMethod
from archinstall.lib.models.users import Password, User


class FakePacman:
	def __init__(self) -> None:
		self.packages: list[str] = []

	def strap(self, package: str) -> None:
		self.packages.append(package)


class FakeInstaller:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.pacman = FakePacman()


class FakeWorker:
	def __init__(self, _cmd: str, peek_output: bool = False, output: str = 'alice:key-data') -> None:
		self.peek_output = peek_output
		self.output = output
		self._trace_log = b''
		self.closed = False

	def __enter__(self) -> Self:
		return self

	def __exit__(self, *_args: object) -> None:
		self.closed = True

	def is_alive(self) -> bool:
		return False

	def write(self, _data: bytes) -> int:
		return 0

	def decode(self) -> str:
		return self.output


def test_u2f_passwordless_sudo_false_round_trips() -> None:
	config = U2FLoginConfiguration(U2FLoginMethod.SecondFactor, passwordless_sudo=False)

	parsed = U2FLoginConfiguration.parse_arg(config.json())

	assert parsed == config
	assert parsed is not None
	assert parsed.passwordless_sudo is False


def test_u2f_enrollment_uses_worker_context_and_writes_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
	(tmp_path / 'etc').mkdir()
	installer = FakeInstaller(tmp_path)
	worker = FakeWorker('')

	monkeypatch.setattr(authentication_handler_module, 'SysCommandWorker', lambda *_args, **_kwargs: worker)

	AuthenticationHandler()._configure_u2f_mapping(
		installer,  # type: ignore[arg-type]
		U2FLoginConfiguration(U2FLoginMethod.SecondFactor),
		[User('alice', Password(enc_password='hash'), False)],
		'arch-test',
	)

	assert worker.closed
	assert installer.pacman.packages == ['pam-u2f']
	assert (tmp_path / 'etc/u2f_mappings').read_text() == 'alice:key-data'


def test_u2f_enrollment_rejects_empty_command_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
	(tmp_path / 'etc').mkdir()
	installer = FakeInstaller(tmp_path)
	worker = FakeWorker('', output='')

	monkeypatch.setattr(authentication_handler_module, 'SysCommandWorker', lambda *_args, **_kwargs: worker)

	with pytest.raises(ValueError, match='no registration data'):
		AuthenticationHandler()._configure_u2f_mapping(
			installer,  # type: ignore[arg-type]
			U2FLoginConfiguration(U2FLoginMethod.SecondFactor),
			[User('alice', Password(enc_password='hash'), False)],
			'arch-test',
		)

	assert worker.closed
