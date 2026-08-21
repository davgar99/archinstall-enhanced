from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Any, NotRequired, Self, TypedDict, override

from archinstall.lib.models.config import SubConfig
from archinstall.lib.translationhandler import tr


class PowerManagement(StrEnum):
	POWER_PROFILES_DAEMON = 'power-profiles-daemon'
	TUNED = auto()


class PowerManagementConfigSerialization(TypedDict):
	power_management: str


class BluetoothConfigSerialization(TypedDict):
	enabled: bool


class Audio(StrEnum):
	NO_AUDIO = 'No audio server'
	PIPEWIRE = auto()
	PULSEAUDIO = auto()


class AudioConfigSerialization(TypedDict):
	audio: str


class PrintServiceConfigSerialization(TypedDict):
	enabled: bool


class Firewall(StrEnum):
	UFW = auto()
	FWD = 'firewalld'


class FirewallConfigSerialization(TypedDict):
	firewall: str


class FontPackage(StrEnum):
	NOTO = 'noto-fonts'
	EMOJI = 'noto-fonts-emoji'
	CJK = 'noto-fonts-cjk'
	LIBERATION = 'ttf-liberation'
	DEJAVU = 'ttf-dejavu'

	def description(self) -> str:
		match self:
			case FontPackage.NOTO:
				return tr('Unicode font coverage for most languages')
			case FontPackage.EMOJI:
				return tr('color emoji for browsers and apps')
			case FontPackage.CJK:
				return tr('Chinese, Japanese, Korean characters')
			case FontPackage.LIBERATION:
				return tr('Arial/Times/Courier replacement, Cyrillic support for Steam/games')
			case FontPackage.DEJAVU:
				return tr('wide Unicode coverage, good fallback font')


class FontsConfigSerialization(TypedDict):
	fonts: list[str]


class ZramAlgorithm(StrEnum):
	ZSTD = auto()
	LZO_RLE = 'lzo-rle'
	LZO = auto()
	LZ4 = auto()
	LZ4HC = auto()

	def generator_value(self) -> str:
		# Zstd level 3 is a conservative balance of compression, latency, and CPU use.
		# Algorithms without a supported level setting remain the fast primary
		# compressor and use zstd only to recompress cold, poorly compressed pages.
		if self == ZramAlgorithm.ZSTD:
			return 'zstd(level=3)'
		return f'{self.value} zstd(level=3) (type=idle,threshold=3000)'


class ApplicationSerialization(TypedDict):
	bluetooth_config: NotRequired[BluetoothConfigSerialization]
	audio_config: NotRequired[AudioConfigSerialization]
	power_management_config: NotRequired[PowerManagementConfigSerialization]
	print_service_config: NotRequired[PrintServiceConfigSerialization]
	firewall_config: NotRequired[FirewallConfigSerialization]
	fonts_config: NotRequired[FontsConfigSerialization]


@dataclass
class AudioConfiguration:
	audio: Audio

	def json(self) -> AudioConfigSerialization:
		return {
			'audio': self.audio.value,
		}

	@classmethod
	def parse_arg(cls, arg: dict[str, Any]) -> Self:
		return cls(
			Audio(arg['audio']),
		)


@dataclass
class BluetoothConfiguration:
	enabled: bool

	def json(self) -> BluetoothConfigSerialization:
		return {'enabled': self.enabled}

	@classmethod
	def parse_arg(cls, arg: BluetoothConfigSerialization) -> Self:
		return cls(arg['enabled'])


@dataclass
class PowerManagementConfiguration:
	power_management: PowerManagement

	def json(self) -> PowerManagementConfigSerialization:
		return {
			'power_management': self.power_management.value,
		}

	@classmethod
	def parse_arg(cls, arg: PowerManagementConfigSerialization) -> Self:
		return cls(
			PowerManagement(arg['power_management']),
		)


@dataclass
class PrintServiceConfiguration:
	enabled: bool

	def json(self) -> PrintServiceConfigSerialization:
		return {'enabled': self.enabled}

	@classmethod
	def parse_arg(cls, arg: PrintServiceConfigSerialization) -> Self:
		return cls(arg['enabled'])


@dataclass
class FirewallConfiguration:
	firewall: Firewall

	def json(self) -> FirewallConfigSerialization:
		return {
			'firewall': self.firewall.value,
		}

	@classmethod
	def parse_arg(cls, arg: dict[str, Any]) -> Self:
		return cls(
			Firewall(arg['firewall']),
		)


@dataclass
class FontsConfiguration:
	fonts: list[FontPackage]

	def json(self) -> FontsConfigSerialization:
		return {'fonts': [f.value for f in self.fonts]}

	@classmethod
	def parse_arg(cls, arg: FontsConfigSerialization) -> Self:
		return cls(fonts=[FontPackage(f) for f in arg['fonts']])


class ZramConfigSerialization(TypedDict):
	enabled: bool
	algorithm: str
	swappiness_tweaks: NotRequired[bool]


@dataclass(frozen=True)
class ZramConfiguration(SubConfig):
	enabled: bool
	algorithm: ZramAlgorithm = ZramAlgorithm.ZSTD
	swappiness_tweaks: bool = False

	@classmethod
	def parse_arg(cls, arg: bool | ZramConfigSerialization | dict[str, Any]) -> Self:
		if isinstance(arg, bool):
			return cls(enabled=arg)

		enabled = bool(arg.get('enabled', True))
		algo = arg.get('algorithm', arg.get('algo', ZramAlgorithm.ZSTD.value))
		if algo == 'lzo-rle zstd(level=3) (type=idle)':
			algo = ZramAlgorithm.ZSTD.value
		swappiness_tweaks = bool(arg.get('swappiness_tweaks', arg.get('swappiness', False)))
		return cls(
			enabled=enabled,
			algorithm=ZramAlgorithm(algo),
			swappiness_tweaks=swappiness_tweaks,
		)

	@override
	def json(self) -> ZramConfigSerialization:
		return {
			'enabled': self.enabled,
			'algorithm': self.algorithm.value,
			'swappiness_tweaks': self.swappiness_tweaks,
		}

	@override
	def summary(self) -> list[str]:
		status = tr('Enabled') if self.enabled else tr('Disabled')
		out = [f'{tr("Zram")}: {status}']

		if self.enabled:
			out.append(f'{tr("Zram algorithm")}: {self.algorithm.value}')
			tweak_status = tr('Enabled') if self.swappiness_tweaks else tr('Disabled')
			out.append(f'{tr("Swappiness tweaks")}: {tweak_status}')

		return out


@dataclass
class ApplicationConfiguration(SubConfig):
	bluetooth_config: BluetoothConfiguration | None = None
	audio_config: AudioConfiguration | None = None
	power_management_config: PowerManagementConfiguration | None = None
	print_service_config: PrintServiceConfiguration | None = None
	firewall_config: FirewallConfiguration | None = None
	fonts_config: FontsConfiguration | None = None

	@classmethod
	def parse_arg(
		cls,
		args: dict[str, Any] | None = None,
		old_audio_config: dict[str, Any] | None = None,
	) -> Self:
		app_config = cls()

		if args and (bluetooth_config := args.get('bluetooth_config')) is not None:
			app_config.bluetooth_config = BluetoothConfiguration.parse_arg(bluetooth_config)

		# deprecated: backwards compatibility
		if old_audio_config is not None:
			app_config.audio_config = AudioConfiguration.parse_arg(old_audio_config)

		if args and (audio_config := args.get('audio_config')) is not None:
			app_config.audio_config = AudioConfiguration.parse_arg(audio_config)

		if args and (power_management_config := args.get('power_management_config')) is not None:
			app_config.power_management_config = PowerManagementConfiguration.parse_arg(power_management_config)

		if args and (print_service_config := args.get('print_service_config')) is not None:
			app_config.print_service_config = PrintServiceConfiguration.parse_arg(print_service_config)

		if args and (firewall_config := args.get('firewall_config')) is not None:
			app_config.firewall_config = FirewallConfiguration.parse_arg(firewall_config)

		if args and (fonts_config := args.get('fonts_config')) is not None:
			app_config.fonts_config = FontsConfiguration.parse_arg(fonts_config)

		return app_config

	@override
	def json(self) -> ApplicationSerialization:
		config: ApplicationSerialization = {}

		if self.bluetooth_config:
			config['bluetooth_config'] = self.bluetooth_config.json()

		if self.audio_config:
			config['audio_config'] = self.audio_config.json()

		if self.power_management_config:
			config['power_management_config'] = self.power_management_config.json()

		if self.print_service_config:
			config['print_service_config'] = self.print_service_config.json()

		if self.firewall_config:
			config['firewall_config'] = self.firewall_config.json()

		if self.fonts_config:
			config['fonts_config'] = self.fonts_config.json()

		return config

	@override
	def summary(self) -> list[str]:
		out: list[str] = []

		if self.bluetooth_config:
			status = tr('Enabled') if self.bluetooth_config.enabled else tr('Disabled')
			out.append(f'{tr("Bluetooth")}: {status}')

		if self.audio_config:
			out.append(f'{tr("Audio server")}: {self.audio_config.audio.value}')

		if self.power_management_config:
			out.append(f'{tr("Power management")}: {self.power_management_config.power_management.value}')

		if self.print_service_config:
			status = tr('Enabled') if self.print_service_config.enabled else tr('Disabled')
			out.append(f'{tr("Print service")}: {status}')

		if self.firewall_config:
			out.append(f'{tr("Firewall")}: {self.firewall_config.firewall.value}')

		if self.fonts_config and self.fonts_config.fonts:
			fonts = ', '.join(f.value for f in self.fonts_config.fonts)
			out.append(f'{tr("Extra fonts")}: {fonts}')

		return out
