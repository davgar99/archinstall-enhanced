from pathlib import Path

from pytest import MonkeyPatch

from archinstall.applications.graphics_extras import GraphicsExtrasApp
from archinstall.lib.applications.application_handler import ApplicationHandler
from archinstall.lib.gaming.gaming_handler import GamingHandler
from archinstall.lib.hardware import CPUVendor, GfxDriver, SysInfo
from archinstall.lib.models import Audio
from archinstall.lib.models.application import (
	ApplicationConfiguration,
	AudioConfiguration,
	BluetoothConfiguration,
	Firewall,
	FirewallConfiguration,
	FirmwareConfiguration,
	FontPackage,
	FontsConfiguration,
	MultimediaConfiguration,
	PowerManagement,
	PowerManagementConfiguration,
	PrintServiceConfiguration,
)
from archinstall.lib.models.gaming import (
	CPUScheduler,
	CPUSchedulerConfiguration,
	GamingConfiguration,
	NTSyncConfiguration,
)
from archinstall.lib.models.network import DnsResolver, NetworkConfiguration, NicType
from archinstall.lib.models.users import Password, User


class FakeInstaller:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.packages: list[str] = []
		self.services: list[str] = []
		self.chroot_commands: list[str] = []
		self.mkinitcpio_calls: list[list[str]] = []

	def add_additional_packages(self, packages: str | list[str]) -> None:
		if isinstance(packages, str):
			packages = [packages]
		self.packages.extend(packages)

	def enable_service(self, services: str | list[str]) -> None:
		if isinstance(services, str):
			services = [services]
		self.services.extend(services)

	def arch_chroot(self, command: str) -> None:
		self.chroot_commands.append(command)

	def mkinitcpio(self, flags: list[str]) -> bool:
		self.mkinitcpio_calls.append(flags)
		return True


def test_application_handler_installs_complete_selected_stack(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
	installer = FakeInstaller(tmp_path)
	ufw_conf = tmp_path / 'etc/ufw/ufw.conf'
	ufw_conf.parent.mkdir(parents=True)
	ufw_conf.write_text('ENABLED=no\nLOGLEVEL=low\n')
	nsswitch = tmp_path / 'etc/nsswitch.conf'
	nsswitch.write_text('passwd: files\nhosts: files dns\n')
	monkeypatch.setattr(SysInfo, 'requires_sof_fw', lambda: True)
	monkeypatch.setattr(SysInfo, 'requires_alsa_fw', lambda: True)
	config = ApplicationConfiguration(
		bluetooth_config=BluetoothConfiguration(enabled=True),
		audio_config=AudioConfiguration(audio=Audio.PIPEWIRE),
		multimedia_config=MultimediaConfiguration(enabled=True),
		firmware_config=FirmwareConfiguration(enabled=True),
		power_management_config=PowerManagementConfiguration(power_management=PowerManagement.TUNED),
		print_service_config=PrintServiceConfiguration(enabled=True),
		firewall_config=FirewallConfiguration(firewall=Firewall.UFW),
		fonts_config=FontsConfiguration(fonts=[FontPackage.NOTO, FontPackage.EMOJI]),
	)
	network = NetworkConfiguration(NicType.NM, dns_resolver=DnsResolver.DNSMASQ)

	ApplicationHandler().install_applications(installer, config, network_config=network)  # type: ignore[arg-type]

	expected_packages = {
		'bluez',
		'bluez-utils',
		'sof-firmware',
		'alsa-firmware',
		'pipewire',
		'pipewire-alsa',
		'pipewire-jack',
		'pipewire-pulse',
		'gst-plugin-pipewire',
		'libpulse',
		'wireplumber',
		'rtkit',
		'gstreamer',
		'gst-plugins-base',
		'gst-plugins-good',
		'gst-plugins-bad',
		'gst-plugins-ugly',
		'gst-libav',
		'gst-plugin-va',
		'ffmpeg',
		'fwupd',
		'tuned',
		'tuned-ppd',
		'cups',
		'system-config-printer',
		'cups-pk-helper',
		'ghostscript',
		'avahi',
		'nss-mdns',
		'ufw',
		'noto-fonts',
		'noto-fonts-emoji',
	}
	expected_services = {
		'bluetooth.service',
		'fwupd-refresh.timer',
		'tuned.service',
		'tuned-ppd.service',
		'cups.service',
		'avahi-daemon.service',
		'ufw.service',
	}
	assert set(installer.packages) == expected_packages
	assert len(installer.packages) == len(expected_packages)
	assert set(installer.services) == expected_services
	assert len(installer.services) == len(expected_services)
	assert ufw_conf.read_text() == 'ENABLED=yes\nLOGLEVEL=low\n'
	assert nsswitch.read_text() == 'passwd: files\nhosts: files mdns_minimal [NOTFOUND=return] dns\n'


def test_gaming_handler_installs_complete_selected_stack(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
	installer = FakeInstaller(tmp_path)
	monkeypatch.setattr(SysInfo, 'cpu_vendor', lambda: CPUVendor.AMD)
	config = GamingConfiguration(
		cpu_scheduler_config=CPUSchedulerConfiguration(scheduler=CPUScheduler.LAVD),
		ntsync_config=NTSyncConfiguration(enabled=True),
		gamemode=True,
		mangohud=True,
		gamescope=True,
		disable_watchdog=True,
		increase_vm_max_map_count=True,
		increase_shader_cache=True,
		disable_playstation_touchpad=True,
	)
	user = User('traveler', Password(enc_password='test'), sudo=True)

	GamingHandler().install_gaming(installer, config, [user])  # type: ignore[arg-type]

	assert installer.packages == [
		'scx-scheds',
		'scx-tools',
		'ntsync-autoload',
		'gamemode',
		'lib32-gamemode',
		'mangohud',
		'lib32-mangohud',
		'gamescope',
	]
	assert installer.services == ['scx_loader.service']
	assert installer.chroot_commands == ['usermod -aG gamemode traveler']
	assert installer.mkinitcpio_calls == [['-P']]
	assert (tmp_path / 'etc/scx_loader/config.toml').read_text() == 'default_sched = "scx_lavd"\ndefault_mode = "Gaming"\n'
	assert (tmp_path / 'etc/modprobe.d/disable-watchdog.conf').read_text() == 'blacklist sp5100_tco\n'
	assert 'vm.max_map_count = 2147483642' in (tmp_path / 'etc/sysctl.d/80-gamecompatibility.conf').read_text()
	assert 'MESA_SHADER_CACHE_MAX_SIZE=12G' in (tmp_path / 'etc/environment.d/90-gaming-shader-cache.conf').read_text()
	assert (tmp_path / 'etc/udev/rules.d/72-playstation-controller-touchpads.rules').read_text().count('ENV{LIBINPUT_IGNORE_DEVICE}="1"') == 4


def test_graphics_extras_install_combines_multilib_and_opencl_without_duplicates(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	GraphicsExtrasApp().install(installer, True, True, GfxDriver.AllOpenSource)  # type: ignore[arg-type]

	assert installer.packages == [
		'lib32-mesa',
		'lib32-vulkan-radeon',
		'lib32-vulkan-intel',
		'lib32-vulkan-nouveau',
		'lib32-vulkan-icd-loader',
		'opencl-mesa',
		'ocl-icd',
		'clinfo',
		'lib32-opencl-mesa',
	]
	assert (tmp_path / 'etc/environment.d/90-opencl.conf').read_text().endswith('RUSTICL_ENABLE=radeonsi,iris,nouveau\n')


def test_handlers_with_empty_config_leave_target_untouched(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	ApplicationHandler().install_applications(installer, ApplicationConfiguration())  # type: ignore[arg-type]
	GamingHandler().install_gaming(installer, GamingConfiguration(install_32bit_graphics=False))  # type: ignore[arg-type]
	GraphicsExtrasApp().install(installer, False, False, None)  # type: ignore[arg-type]

	assert installer.packages == []
	assert installer.services == []
	assert installer.chroot_commands == []
	assert installer.mkinitcpio_calls == []
	assert list(tmp_path.iterdir()) == []
