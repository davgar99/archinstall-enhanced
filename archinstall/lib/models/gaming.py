from dataclasses import dataclass
from enum import StrEnum
from typing import NotRequired, Self, TypedDict, override

from archinstall.lib.models.config import SubConfig
from archinstall.lib.translationhandler import tr


class CPUSchedulerStability(StrEnum):
	STABLE = 'stable'
	EXPERIMENTAL = 'experimental'
	DEPRECATED = 'deprecated'

	def display_name(self) -> str:
		match self:
			case CPUSchedulerStability.STABLE:
				return tr('Production ready (stable)')
			case CPUSchedulerStability.EXPERIMENTAL:
				return tr('Experimental')
			case CPUSchedulerStability.DEPRECATED:
				return tr('Deprecated')

		raise ValueError(f'Unhandled CPU scheduler stability: {self}')


class CPUScheduler(StrEnum):
	# Production-ready schedulers explicitly documented as such upstream and
	# shipped by Arch Linux's scx-scheds package.
	LAVD = 'scx_lavd'
	BPFLAND = 'scx_bpfland'
	FLASH = 'scx_flash'
	RUSTY = 'scx_rusty'
	P2DQ = 'scx_p2dq'
	COSMOS = 'scx_cosmos'
	BEERLAND = 'scx_beerland'

	# Experimental schedulers that are also shipped by Arch Linux's
	# scx-scheds package.
	CAKE = 'scx_cake'
	FLOW = 'scx_flow'
	TICKLESS = 'scx_tickless'

	def stability(self) -> CPUSchedulerStability:
		match self:
			case (
				CPUScheduler.LAVD
				| CPUScheduler.BPFLAND
				| CPUScheduler.FLASH
				| CPUScheduler.RUSTY
				| CPUScheduler.P2DQ
				| CPUScheduler.COSMOS
				| CPUScheduler.BEERLAND
			):
				return CPUSchedulerStability.STABLE
			case CPUScheduler.CAKE | CPUScheduler.FLOW | CPUScheduler.TICKLESS:
				return CPUSchedulerStability.EXPERIMENTAL

		raise ValueError(f'Unhandled CPU scheduler: {self}')


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
