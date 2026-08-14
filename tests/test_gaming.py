from pathlib import Path

import pytest

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
	stable = {
		CPUScheduler.BEERLAND,
		CPUScheduler.BPFLAND,
		CPUScheduler.COSMOS,
		CPUScheduler.FLASH,
		CPUScheduler.LAVD,
		CPUScheduler.LAYERED,
		CPUScheduler.P2DQ,
		CPUScheduler.PANDEMONIUM,
		CPUScheduler.RUSTLAND,
		CPUScheduler.RUSTY,
	}
	experimental = {
		CPUScheduler.CAKE,
		CPUScheduler.CHAOS,
		CPUScheduler.FLOW,
		CPUScheduler.FORGE,
		CPUScheduler.TICKLESS,
	}

	assert set(CPUSchedulerStability) == {
		CPUSchedulerStability.STABLE,
		CPUSchedulerStability.EXPERIMENTAL,
	}
	assert {scheduler for scheduler in CPUScheduler if scheduler.stability() == CPUSchedulerStability.STABLE} == stable
	assert {scheduler for scheduler in CPUScheduler if scheduler.stability() == CPUSchedulerStability.EXPERIMENTAL} == experimental
	assert stable | experimental == set(CPUScheduler)


def test_cpu_scheduler_loader_support() -> None:
	unsupported = {
		CPUScheduler.CHAOS,
		CPUScheduler.LAYERED,
	}

	assert {scheduler for scheduler in CPUScheduler if not scheduler.supported_by_scx_loader()} == unsupported


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


def test_cpu_scheduler_install_rejects_unsupported_loader_scheduler(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	config = CPUSchedulerConfiguration(scheduler=CPUScheduler.LAYERED)

	with pytest.raises(ValueError, match='scx_layered is not supported by scx_loader'):
		CPUSchedulerApp().install(installer, config)  # type: ignore[arg-type]
