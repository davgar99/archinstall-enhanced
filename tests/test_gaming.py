from pathlib import Path

from archinstall.applications.cpu_scheduler import CPUSchedulerApp
from archinstall.lib.args import ArchConfig, ArchConfigType, Arguments
from archinstall.lib.models.gaming import (
	CPUScheduler,
	CPUSchedulerConfiguration,
	CPUSchedulerStability,
	GamingConfiguration,
)


class FakeInstaller:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.packages: list[str] = []
		self.services: list[str] = []

	def add_additional_packages(self, packages: list[str]) -> None:
		self.packages.extend(packages)

	def enable_service(self, service: str) -> None:
		self.services.append(service)


def test_cpu_scheduler_stability() -> None:
	assert CPUScheduler.LAVD.stability() == CPUSchedulerStability.STABLE
	assert CPUScheduler.CAKE.stability() == CPUSchedulerStability.EXPERIMENTAL
	assert not any(scheduler.stability() == CPUSchedulerStability.DEPRECATED for scheduler in CPUScheduler)


def test_gaming_configuration_roundtrip() -> None:
	gaming_config = GamingConfiguration(
		cpu_scheduler_config=CPUSchedulerConfiguration(scheduler=CPUScheduler.LAVD),
	)
	serialized = gaming_config.json()

	assert serialized == {'cpu_scheduler_config': {'scheduler': 'scx_lavd'}}
	assert GamingConfiguration.parse_arg(serialized) == gaming_config

	arch_config = ArchConfig(gaming_config=gaming_config)
	assert arch_config.safe_config()[ArchConfigType.GAMING_CONFIG] == serialized
	assert ArchConfig.from_config({'gaming_config': serialized}, Arguments()).gaming_config == gaming_config


def test_cpu_scheduler_install(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	config = CPUSchedulerConfiguration(scheduler=CPUScheduler.LAVD)

	CPUSchedulerApp().install(installer, config)  # type: ignore[arg-type]

	assert installer.packages == ['scx-scheds', 'scx-tools']
	assert installer.services == ['scx_loader.service']
	assert (tmp_path / 'etc/scx_loader/config.toml').read_text() == (
		'default_sched = "scx_lavd"\n'
		'default_mode = "Gaming"\n'
	)
