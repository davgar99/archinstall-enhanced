from typing import override

from archinstall.lib.menu.abstract_menu import AbstractSubMenu
from archinstall.lib.menu.helpers import Confirmation, Selection
from archinstall.lib.models.application import (
	ApplicationConfiguration,
	Audio,
	AudioConfiguration,
	BluetoothConfiguration,
	Firewall,
	FirewallConfiguration,
	FirmwareConfiguration,
	FirmwarePackageMode,
	FirmwarePackagesConfiguration,
	FirmwareVendor,
	FontPackage,
	FontsConfiguration,
	KernelHeadersConfiguration,
	MultimediaConfiguration,
	PowerManagement,
	PowerManagementConfiguration,
	PrintServiceConfiguration,
)
from archinstall.lib.translationhandler import tr
from archinstall.tui.menu_item import MenuItem, MenuItemGroup, MenuItemRole
from archinstall.tui.result import ResultType


class ApplicationMenu(AbstractSubMenu[ApplicationConfiguration]):
	def __init__(self, preset: ApplicationConfiguration | None = None):
		self._app_config = preset or ApplicationConfiguration()
		menu_options = self._define_menu_options()
		self._item_group = MenuItemGroup(menu_options, checkmarks=True)
		super().__init__(self._item_group, config=self._app_config, allow_reset=True)

	@override
	async def show(self) -> ApplicationConfiguration | None:
		_ = await super().show()
		return self._app_config

	def _define_menu_options(self) -> list[MenuItem]:
		return [
			MenuItem(text=tr('Hardware'), role=MenuItemRole.SECTION),
			MenuItem(
				text=tr('Kernel firmware'),
				action=select_firmware_packages,
				value=self._app_config.firmware_packages_config,
				preview_action=self._prev_firmware_packages,
				key='firmware_packages_config',
			),
			MenuItem(
				text=tr('Kernel headers'),
				action=select_kernel_headers,
				value=self._app_config.kernel_headers_config,
				preview_action=self._prev_kernel_headers,
				key='kernel_headers_config',
			),
			MenuItem(
				text=tr('Bluetooth'),
				action=select_bluetooth,
				value=self._app_config.bluetooth_config,
				preview_action=self._prev_bluetooth,
				key='bluetooth_config',
			),
			MenuItem(
				text=tr('Print service'),
				action=select_print_service,
				preview_action=self._prev_print_service,
				key='print_service_config',
			),
			MenuItem(
				text=tr('Firmware updates'),
				action=select_firmware,
				value=self._app_config.firmware_config,
				preview_action=self._prev_firmware,
				key='firmware_config',
			),
			MenuItem(text=tr('Media and appearance'), role=MenuItemRole.SECTION),
			MenuItem(
				text=tr('Audio'),
				action=select_audio,
				preview_action=self._prev_audio,
				key='audio_config',
			),
			MenuItem(
				text=tr('Multimedia codecs'),
				action=select_multimedia,
				value=self._app_config.multimedia_config,
				preview_action=self._prev_multimedia,
				key='multimedia_config',
			),
			MenuItem(
				text=tr('Additional fonts'),
				action=select_fonts,
				value=self._app_config.fonts_config,
				preview_action=self._prev_fonts,
				key='fonts_config',
			),
			MenuItem(text=tr('System'), role=MenuItemRole.SECTION),
			MenuItem(
				text=tr('Power management'),
				action=select_power_management,
				preview_action=self._prev_power_management,
				key='power_management_config',
			),
			MenuItem(
				text=tr('Firewall'),
				action=select_firewall,
				value=self._app_config.firewall_config,
				preview_action=self._prev_firewall,
				key='firewall_config',
			),
		]

	def _prev_firmware_packages(self, item: MenuItem) -> str | None:
		if item.value is None:
			return None
		config: FirmwarePackagesConfiguration = item.value
		text = f'{tr("Kernel firmware")}: {config.mode.display_msg()}'
		if config.vendors:
			text += '\n' + ', '.join(vendor.value for vendor in config.vendors)
		return text

	def _prev_kernel_headers(self, item: MenuItem) -> str | None:
		if item.value is None:
			return None
		config: KernelHeadersConfiguration = item.value
		status = tr('Enabled') if config.enabled else tr('Disabled')
		return f'{tr("Kernel headers")}: {status}'

	def _prev_power_management(self, item: MenuItem) -> str | None:
		if item.value is not None:
			config: PowerManagementConfiguration = item.value
			return f'{tr("Power management")}: {config.power_management.value}'
		return None

	def _prev_bluetooth(self, item: MenuItem) -> str | None:
		if item.value is not None:
			config: BluetoothConfiguration = item.value
			status = tr('Enabled') if config.enabled else tr('Disabled')
			return f'{tr("Bluetooth")}: {status}'
		return None

	def _prev_audio(self, item: MenuItem) -> str | None:
		if item.value is not None:
			config: AudioConfiguration = item.value
			return f'{tr("Audio")}: {config.audio.value}'
		return None

	def _prev_print_service(self, item: MenuItem) -> str | None:
		if item.value is not None:
			config: PrintServiceConfiguration = item.value
			status = tr('Enabled') if config.enabled else tr('Disabled')
			return f'{tr("Print service")}: {status}'
		return None

	def _prev_multimedia(self, item: MenuItem) -> str | None:
		if item.value is not None:
			config: MultimediaConfiguration = item.value
			status = tr('Enabled') if config.enabled else tr('Disabled')
			return f'{tr("Multimedia codecs")}: {status}'
		return None

	def _prev_firmware(self, item: MenuItem) -> str | None:
		if item.value is not None:
			config: FirmwareConfiguration = item.value
			status = tr('Enabled') if config.enabled else tr('Disabled')
			return f'{tr("Firmware updates")}: {status}'
		return None

	def _prev_firewall(self, item: MenuItem) -> str | None:
		if item.value is not None:
			config: FirewallConfiguration = item.value
			ssh_status = tr('Allowed') if config.allow_ssh else tr('Blocked')
			return f'{tr("Firewall")}: {config.firewall.value}\n{tr("Incoming SSH")}: {ssh_status}'
		return None

	def _prev_fonts(self, item: MenuItem) -> str | None:
		if item.value is not None:
			config: FontsConfiguration = item.value
			packages = ', '.join(f.value for f in config.fonts)
			return f'{tr("Additional fonts")}: {packages}'
		return None


async def select_firmware_packages(preset: FirmwarePackagesConfiguration | None = None) -> FirmwarePackagesConfiguration | None:
	items = [MenuItem(mode.display_msg(), value=mode) for mode in FirmwarePackageMode]
	group = MenuItemGroup(items, sort_items=False)
	group.set_default_by_value(preset.mode if preset else FirmwarePackageMode.FULL)
	result = await Selection[FirmwarePackageMode](
		group,
		header=tr('Choose how Linux firmware packages should be installed.'),
		allow_skip=True,
		allow_reset=True,
	).show()

	mode = preset.mode if preset else FirmwarePackageMode.FULL
	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Reset:
			return None
		case ResultType.Selection:
			mode = result.get_value()

	if mode != FirmwarePackageMode.VENDOR:
		return FirmwarePackagesConfiguration(mode=mode)

	vendor_items = [MenuItem(vendor.value, value=vendor) for vendor in FirmwareVendor]
	vendor_group = MenuItemGroup(vendor_items, sort_items=True)
	if preset and preset.mode == FirmwarePackageMode.VENDOR:
		vendor_group.set_selected_by_value(preset.vendors)
	vendor_result = await Selection[FirmwareVendor](
		vendor_group,
		header=tr('Select every firmware vendor needed by this machine.'),
		allow_skip=True,
		allow_reset=True,
		multi=True,
	).show()
	match vendor_result.type_:
		case ResultType.Selection:
			return FirmwarePackagesConfiguration(mode=mode, vendors=vendor_result.get_values())
		case ResultType.Skip:
			return preset if preset else FirmwarePackagesConfiguration(mode=mode)
		case ResultType.Reset:
			return FirmwarePackagesConfiguration(mode=mode)


async def select_kernel_headers(preset: KernelHeadersConfiguration | None = None) -> KernelHeadersConfiguration | None:
	result = await Confirmation(
		header=tr('Install matching header packages for every selected kernel? This is useful for DKMS and out-of-tree modules.'),
		allow_skip=True,
	).show()
	match result.type_:
		case ResultType.Selection:
			return KernelHeadersConfiguration(enabled=result.get_value())
		case ResultType.Skip:
			return preset
		case _:
			raise ValueError('Unhandled result type')


async def select_power_management(preset: PowerManagementConfiguration | None = None) -> PowerManagementConfiguration | None:
	group = MenuItemGroup.from_enum(PowerManagement)
	group.set_default_by_value(PowerManagement.POWER_PROFILES_DAEMON)
	result = await Selection[PowerManagement](group, allow_skip=True, allow_reset=True).show()
	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Selection:
			return PowerManagementConfiguration(power_management=result.get_value())
		case ResultType.Reset:
			return None


async def select_bluetooth(preset: BluetoothConfiguration | None) -> BluetoothConfiguration | None:
	result = await Confirmation(header=tr('Would you like to configure Bluetooth?') + '\n', allow_skip=True).show()
	match result.type_:
		case ResultType.Selection:
			return BluetoothConfiguration(result.get_value())
		case ResultType.Skip:
			return preset
		case _:
			raise ValueError('Unhandled result type')


async def select_print_service(preset: PrintServiceConfiguration | None) -> PrintServiceConfiguration | None:
	result = await Confirmation(header=tr('Would you like to configure the print service?') + '\n', allow_skip=True).show()
	match result.type_:
		case ResultType.Selection:
			return PrintServiceConfiguration(result.get_value())
		case ResultType.Skip:
			return preset
		case _:
			raise ValueError('Unhandled result type')


async def select_audio(preset: AudioConfiguration | None = None) -> AudioConfiguration | None:
	items = [MenuItem(a.value, value=a) for a in Audio]
	group = MenuItemGroup(items)
	result = await Selection[Audio](group, header=tr('Select audio configuration'), allow_skip=True).show()
	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Selection:
			return AudioConfiguration(audio=result.get_value())
		case ResultType.Reset:
			raise ValueError('Unhandled result type')


async def select_multimedia(preset: MultimediaConfiguration | None = None) -> MultimediaConfiguration | None:
	result = await Confirmation(
		header=tr(
			'Install a complete GStreamer codec set, FFmpeg, and the VA-API GStreamer plugin? '
			'This supports common audio and video formats and hardware-accelerated playback when the selected GPU supports it.'
		),
		allow_skip=True,
	).show()
	match result.type_:
		case ResultType.Selection:
			return MultimediaConfiguration(result.get_value())
		case ResultType.Skip:
			return preset
		case _:
			raise ValueError('Unhandled result type')


async def select_firmware(preset: FirmwareConfiguration | None = None) -> FirmwareConfiguration | None:
	result = await Confirmation(
		header=tr('Install firmware update support and enable automatic update-metadata refreshes?'),
		allow_skip=True,
	).show()
	match result.type_:
		case ResultType.Selection:
			return FirmwareConfiguration(result.get_value())
		case ResultType.Skip:
			return preset
		case _:
			raise ValueError('Unhandled result type')


async def select_firewall(preset: FirewallConfiguration | None = None) -> FirewallConfiguration | None:
	group = MenuItemGroup.from_enum(Firewall)
	group.set_default_by_value(Firewall.FWD)
	result = await Selection[Firewall](group, allow_skip=True, allow_reset=True).show()
	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Selection:
			firewall = result.get_value()
			ssh_result = await Confirmation(
				header=tr('Allow incoming SSH connections through the firewall?') + '\n',
				allow_skip=True,
			).show()
			if ssh_result.type_ == ResultType.Skip:
				allow_ssh = preset.allow_ssh if preset else False
			else:
				allow_ssh = bool(ssh_result.get_value())
			return FirewallConfiguration(firewall=firewall, allow_ssh=allow_ssh)
		case ResultType.Reset:
			return None


async def select_fonts(preset: FontsConfiguration | None = None) -> FontsConfiguration | None:
	items = [MenuItem(f'{f.value} ({f.description()})', value=f) for f in FontPackage]
	group = MenuItemGroup(items)
	if preset:
		for font in preset.fonts:
			group.set_selected_by_value(font)
	result = await Selection[FontPackage](
		group,
		header=tr('Select font packages to install'),
		allow_skip=True,
		allow_reset=True,
		multi=True,
	).show()
	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Selection:
			selected = result.get_values()
			return FontsConfiguration(fonts=selected) if selected else None
		case ResultType.Reset:
			return None
