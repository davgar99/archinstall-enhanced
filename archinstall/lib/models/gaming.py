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
	BEERLAND = 'scx_beerland'
	BPFLAND = 'scx_bpfland'
	CAKE = 'scx_cake'
	COSMOS = 'scx_cosmos'
	FLASH = 'scx_flash'
	FLOW = 'scx_flow'
	FORGE = 'scx_forge'
	LAVD = 'scx_lavd'
	P2DQ = 'scx_p2dq'
	PANDEMONIUM = 'scx_pandemonium'
	RUSTLAND = 'scx_rustland'
	RUSTY = 'scx_rusty'
	TICKLESS = 'scx_tickless'

	def stability(self) -> CPUSchedulerStability:
		return CPU_SCHEDULER_STABILITY[self]


CPU_SCHEDULER_STABILITY: dict[CPUScheduler, CPUSchedulerStability] = {
	CPUScheduler.BEERLAND: CPUSchedulerStability.STABLE,
	CPUScheduler.BPFLAND: CPUSchedulerStability.STABLE,
	CPUScheduler.CAKE: CPUSchedulerStability.EXPERIMENTAL,
	CPUScheduler.COSMOS: CPUSchedulerStability.STABLE,
	CPUScheduler.FLASH: CPUSchedulerStability.STABLE,
	CPUScheduler.FLOW: CPUSchedulerStability.EXPERIMENTAL,
	CPUScheduler.FORGE: CPUSchedulerStability.EXPERIMENTAL,
	CPUScheduler.LAVD: CPUSchedulerStability.STABLE,
	CPUScheduler.P2DQ: CPUSchedulerStability.STABLE,
	CPUScheduler.PANDEMONIUM: CPUSchedulerStability.STABLE,
	CPUScheduler.RUSTLAND: CPUSchedulerStability.STABLE,
	CPUScheduler.RUSTY: CPUSchedulerStability.STABLE,
	CPUScheduler.TICKLESS: CPUSchedulerStability.EXPERIMENTAL,
}


class CPUSchedulerConfigSerialization(TypedDict):
	scheduler: str


class NTSyncConfigSerialization(TypedDict):
	enabled: bool


class GamingConfigSerialization(TypedDict):
	cpu_scheduler_config: NotRequired[CPUSchedulerConfigSerialization]
	ntsync_config: NotRequired[NTSyncConfigSerialization]
	gamemode: NotRequired[bool]
	mangohud: NotRequired[bool]
	gamescope: NotRequired[bool]
	disable_watchdog: NotRequired[bool]
	increase_vm_max_map_count: NotRequired[bool]


@dataclass
class CPUSchedulerConfiguration:
	scheduler: CPUScheduler

	def json(self) -> CPUSchedulerConfigSerialization:
		return {'scheduler': self.scheduler.value}

	@classmethod
	def parse_arg(cls, arg: CPUSchedulerConfigSerialization) -> Self:
		return cls(scheduler=CPUScheduler(arg['scheduler']))


@dataclass
class NTSyncConfiguration:
	enabled: bool

	def json(self) -> NTSyncConfigSerialization:
		return {'enabled': self.enabled}

	@classmethod
	def parse_arg(cls, arg: NTSyncConfigSerialization) -> Self:
		return cls(enabled=arg['enabled'])


@dataclass
class GamingConfiguration(SubConfig):
	cpu_scheduler_config: CPUSchedulerConfiguration | None = None
	ntsync_config: NTSyncConfiguration | None = None
	gamemode: bool | None = None
	mangohud: bool | None = None
	gamescope: bool | None = None
	disable_watchdog: bool | None = None
	increase_vm_max_map_count: bool | None = None

	@classmethod
	def parse_arg(cls, arg: GamingConfigSerialization) -> Self:
		config = cls()

		if cpu_scheduler_config := arg.get('cpu_scheduler_config'):
			config.cpu_scheduler_config = CPUSchedulerConfiguration.parse_arg(cpu_scheduler_config)

		if ntsync_config := arg.get('ntsync_config'):
			config.ntsync_config = NTSyncConfiguration.parse_arg(ntsync_config)

		if 'gamemode' in arg:
			config.gamemode = arg['gamemode']

		if 'mangohud' in arg:
			config.mangohud = arg['mangohud']

		if 'gamescope' in arg:
			config.gamescope = arg['gamescope']

		if 'disable_watchdog' in arg:
			config.disable_watchdog = arg['disable_watchdog']

		if 'increase_vm_max_map_count' in arg:
			config.increase_vm_max_map_count = arg['increase_vm_max_map_count']

		return config

	def requires_multilib(self) -> bool:
		return self.gamemode is True or self.mangohud is True

	@override
	def json(self) -> GamingConfigSerialization:
		config: GamingConfigSerialization = {}

		if self.cpu_scheduler_config:
			config['cpu_scheduler_config'] = self.cpu_scheduler_config.json()

		if self.ntsync_config:
			config['ntsync_config'] = self.ntsync_config.json()

		if self.gamemode is not None:
			config['gamemode'] = self.gamemode

		if self.mangohud is not None:
			config['mangohud'] = self.mangohud

		if self.gamescope is not None:
			config['gamescope'] = self.gamescope

		if self.disable_watchdog is not None:
			config['disable_watchdog'] = self.disable_watchdog

		if self.increase_vm_max_map_count is not None:
			config['increase_vm_max_map_count'] = self.increase_vm_max_map_count

		return config

	@override
	def summary(self) -> list[str]:
		out: list[str] = []

		if self.cpu_scheduler_config:
			out.append(f'{tr("CPU scheduler")}: {self.cpu_scheduler_config.scheduler.value}')

		if self.ntsync_config:
			status = tr('Enabled') if self.ntsync_config.enabled else tr('Disabled')
			out.append(f'{tr("NTSYNC")}: {status}')

		for label, enabled in (
			('SteamOS vm.max_map_count compatibility', self.increase_vm_max_map_count),
			('GameMode', self.gamemode),
			('MangoHud', self.mangohud),
			('Gamescope', self.gamescope),
			('Disable hardware watchdog', self.disable_watchdog),
		):
			if enabled is not None:
				status = tr('Enabled') if enabled else tr('Disabled')
				out.append(f'{tr(label)}: {status}')

		return out
