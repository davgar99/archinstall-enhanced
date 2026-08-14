from dataclasses import dataclass
from enum import StrEnum
from typing import NotRequired, Self, TypedDict, override

from archinstall.lib.models.config import SubConfig
from archinstall.lib.translationhandler import tr


class CPUSchedulerStability(StrEnum):
	STABLE = 'stable'
	EXPERIMENTAL = 'experimental'

	def display_name(self) -> str:
		match self:
			case CPUSchedulerStability.STABLE:
				return tr('Stable')
			case CPUSchedulerStability.EXPERIMENTAL:
				return tr('Experimental')

		raise ValueError(f'Unhandled CPU scheduler stability: {self}')


class CPUScheduler(StrEnum):
	# Schedulers currently shipped by Arch Linux's scx-scheds package.
	BEERLAND = 'scx_beerland'
	BPFLAND = 'scx_bpfland'
	CAKE = 'scx_cake'
	CHAOS = 'scx_chaos'
	COSMOS = 'scx_cosmos'
	FLASH = 'scx_flash'
	FLOW = 'scx_flow'
	FORGE = 'scx_forge'
	LAVD = 'scx_lavd'
	LAYERED = 'scx_layered'
	P2DQ = 'scx_p2dq'
	PANDEMONIUM = 'scx_pandemonium'
	RUSTLAND = 'scx_rustland'
	RUSTY = 'scx_rusty'
	TICKLESS = 'scx_tickless'

	def stability(self) -> CPUSchedulerStability:
		match self:
			case (
				CPUScheduler.BEERLAND
				| CPUScheduler.BPFLAND
				| CPUScheduler.COSMOS
				| CPUScheduler.FLASH
				| CPUScheduler.LAVD
				| CPUScheduler.LAYERED
				| CPUScheduler.P2DQ
				| CPUScheduler.PANDEMONIUM
				| CPUScheduler.RUSTLAND
				| CPUScheduler.RUSTY
			):
				return CPUSchedulerStability.STABLE
			case (
				CPUScheduler.CAKE
				| CPUScheduler.CHAOS
				| CPUScheduler.FLOW
				| CPUScheduler.FORGE
				| CPUScheduler.TICKLESS
			):
				return CPUSchedulerStability.EXPERIMENTAL

		raise ValueError(f'Unhandled CPU scheduler: {self}')

	def supported_by_scx_loader(self) -> bool:
		# scx_loader currently rejects these two package-provided schedulers.
		return self not in (CPUScheduler.CHAOS, CPUScheduler.LAYERED)


class CPUSchedulerConfigSerialization(TypedDict):
	scheduler: str


class GamingConfigSerialization(TypedDict):
	cpu_scheduler_config: NotRequired[CPUSchedulerConfigSerialization]


@dataclass
class CPUSchedulerConfiguration:
	scheduler: CPUScheduler

	def json(self) -> CPUSchedulerConfigSerialization:
		return {'scheduler': self.scheduler.value}

	@classmethod
	def parse_arg(cls, arg: CPUSchedulerConfigSerialization) -> Self:
		return cls(scheduler=CPUScheduler(arg['scheduler']))


@dataclass
class GamingConfiguration(SubConfig):
	cpu_scheduler_config: CPUSchedulerConfiguration | None = None

	@classmethod
	def parse_arg(cls, arg: GamingConfigSerialization) -> Self:
		config = cls()

		if cpu_scheduler_config := arg.get('cpu_scheduler_config'):
			config.cpu_scheduler_config = CPUSchedulerConfiguration.parse_arg(cpu_scheduler_config)

		return config

	@override
	def json(self) -> GamingConfigSerialization:
		config: GamingConfigSerialization = {}

		if self.cpu_scheduler_config:
			config['cpu_scheduler_config'] = self.cpu_scheduler_config.json()

		return config

	@override
	def summary(self) -> list[str]:
		out: list[str] = []

		if self.cpu_scheduler_config:
			out.append(tr('CPU scheduler "{}"').format(self.cpu_scheduler_config.scheduler.value))

		return out
