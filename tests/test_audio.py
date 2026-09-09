from pathlib import Path

from pytest import MonkeyPatch

from archinstall.applications.audio import AudioApp
from archinstall.lib.hardware import SysInfo
from archinstall.lib.models.application import Audio, AudioConfiguration
from archinstall.lib.models.users import Password, User


class FakeInstaller:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.packages: list[str] = []

	def add_additional_packages(self, packages: str | list[str]) -> None:
		if isinstance(packages, str):
			self.packages.append(packages)
		else:
			self.packages.extend(packages)

	def arch_chroot(self, command: str, run_as: str | None = None) -> None:
		raise AssertionError(f'PipeWire installation should not modify user homes: {command}, {run_as}')


def test_pipewire_relies_on_packaged_socket_activation(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
	installer = FakeInstaller(tmp_path)
	user = User('david', Password(enc_password='test'), sudo=True)
	monkeypatch.setattr(SysInfo, 'requires_sof_fw', lambda: False)
	monkeypatch.setattr(SysInfo, 'requires_alsa_fw', lambda: False)

	AudioApp().install(
		installer,  # type: ignore[arg-type]
		AudioConfiguration(Audio.PIPEWIRE),
		[user],
	)

	assert installer.packages == AudioApp().pipewire_packages
	assert not (tmp_path / 'home').exists()


def test_pipewire_enables_system_wide_surround_upmix(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
	installer = FakeInstaller(tmp_path)
	monkeypatch.setattr(SysInfo, 'requires_sof_fw', lambda: False)
	monkeypatch.setattr(SysInfo, 'requires_alsa_fw', lambda: False)

	AudioApp().install(installer, AudioConfiguration(Audio.PIPEWIRE))  # type: ignore[arg-type]

	config = (tmp_path / 'etc/pipewire/pipewire-pulse.conf.d/10-surround-upmix.conf').read_text()
	assert 'channelmix.upmix = true' in config
	assert 'channelmix.upmix-method = psd' in config
	assert 'channelmix.lfe-cutoff = 150.0' in config


def test_pulseaudio_does_not_write_pipewire_configuration(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
	installer = FakeInstaller(tmp_path)
	monkeypatch.setattr(SysInfo, 'requires_sof_fw', lambda: False)
	monkeypatch.setattr(SysInfo, 'requires_alsa_fw', lambda: False)

	AudioApp().install(installer, AudioConfiguration(Audio.PULSEAUDIO))  # type: ignore[arg-type]

	assert not (tmp_path / 'etc/pipewire').exists()
