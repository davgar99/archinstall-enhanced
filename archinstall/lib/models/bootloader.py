import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Self, override

from archinstall.lib.log import warn
from archinstall.lib.models.config import SubConfig
from archinstall.lib.translationhandler import tr


class Bootloader(Enum):
	NO_BOOTLOADER = 'No bootloader'
	Systemd = 'Systemd-boot'
	Grub = 'Grub'
	Efistub = 'Efistub'
	Limine = 'Limine'
	Refind = 'Refind'

	def has_uki_support(self) -> bool:
		return self != Bootloader.NO_BOOTLOADER

	def has_removable_support(self) -> bool:
		match self:
			case Bootloader.Grub | Bootloader.Limine:
				return True
			case _:
				return False

	def has_os_prober_support(self) -> bool:
		return self == Bootloader.Grub

	def is_uefi_only(self) -> bool:
		match self:
			case Bootloader.Systemd | Bootloader.Efistub | Bootloader.Refind:
				return True
			case _:
				return False

	def json(self) -> str:
		return self.value

	@staticmethod
	def get_default(uefi: bool, skip_boot: bool = False) -> Bootloader:
		if skip_boot:
			return Bootloader.NO_BOOTLOADER
		if uefi:
			return Bootloader.Systemd
		return Bootloader.Grub

	@classmethod
	def from_arg(cls, bootloader: str, skip_boot: bool) -> Self:
		# ``skip_boot`` remains part of the public parser API and only affects the
		# default. An explicitly saved "No bootloader" value must round-trip too.
		_ = skip_boot
		bootloader = bootloader.capitalize()
		bootloader_options = [entry.value for entry in cls]

		if bootloader not in bootloader_options:
			values = ', '.join(bootloader_options)
			warn(f'Invalid bootloader value "{bootloader}". Allowed values: {values}')
			sys.exit(1)

		return cls(bootloader)


class PlymouthTheme(Enum):
	BGRT = 'bgrt'
	FADE = 'fade-in'
	GLOW = 'glow'
	SCRIPT = 'script'
	SOLAR = 'solar'
	SPINNER = 'spinner'
	SPINFINITY = 'spinfinity'
	TRIBAR = 'tribar'
	TEXT = 'text'
	DETAILS = 'details'

	@classmethod
	def from_arg(cls, plymouth: str | None) -> Self | None:
		if plymouth is None:
			return None

		plymouth = plymouth.lower()
		values = [entry.value for entry in cls]
		if plymouth not in values:
			warn(f'Invalid plymouth value "{plymouth}". Allowed values: {", ".join(values)}')
			sys.exit(1)
		return cls(plymouth)


@dataclass
class BootloaderConfiguration(SubConfig):
	bootloader: Bootloader
	uki: bool = False
	removable: bool = True
	plymouth: PlymouthTheme | None = None
	os_prober: bool = False

	@override
	def json(self) -> dict[str, Any]:
		data = {
			'bootloader': self.bootloader.json(),
			'uki': self.uki,
			'removable': self.removable,
			'os_prober': self.os_prober,
		}
		if self.plymouth is not None:
			data['plymouth'] = self.plymouth.value
		return data

	@override
	def summary(self) -> list[str]:
		out = [tr('Bootloader "{}"').format(self.bootloader.value)]
		if self.uki:
			out.append(tr('UKI enabled'))
		if self.removable:
			out.append(tr('Removable'))
		if self.os_prober and self.bootloader.has_os_prober_support():
			out.append(f'os-prober: {tr("Enabled")}')
		if self.plymouth is not None:
			out.append(tr('Plymouth "{}"').format(self.plymouth.value))
		return out

	@classmethod
	def parse_arg(cls, config: dict[str, Any], skip_boot: bool) -> Self:
		bootloader = Bootloader.from_arg(config.get('bootloader', ''), skip_boot)
		uki = config.get('uki', False)
		removable = config.get('removable', True)
		plymouth = PlymouthTheme.from_arg(config.get('plymouth', None))
		os_prober = config.get('os_prober', False)
		return cls(bootloader=bootloader, uki=uki, removable=removable, plymouth=plymouth, os_prober=os_prober)

	@classmethod
	def get_default(cls, uefi: bool, skip_boot: bool = False) -> Self:
		bootloader = Bootloader.get_default(uefi, skip_boot)
		removable = uefi and bootloader.has_removable_support()
		uki = uefi and bootloader.has_uki_support()
		return cls(bootloader=bootloader, uki=uki, removable=removable, plymouth=None, os_prober=False)

	def preview(self, uefi: bool) -> str:
		text = f'{tr("Bootloader")}: {self.bootloader.value}\n'
		if uefi and self.bootloader.has_uki_support():
			uki_string = tr('Enabled') if self.uki else tr('Disabled')
			text += f'UKI: {uki_string}\n'
		if uefi and self.bootloader.has_removable_support():
			removable_string = tr('Enabled') if self.removable else tr('Disabled')
			text += f'{tr("Removable")}: {removable_string}\n'
		if self.bootloader.has_os_prober_support():
			os_prober_string = tr('Enabled') if self.os_prober else tr('Disabled')
			text += f'os-prober: {os_prober_string}\n'
		if self.plymouth is not None:
			text += f'{tr("Plymouth")}: {self.plymouth.value}\n'
		return text
