from typing import override

from archinstall.lib.menu.abstract_menu import AbstractSubMenu
from archinstall.lib.menu.helpers import Confirmation, Selection
from archinstall.lib.models.application import (
	ApplicationConfiguration,
	Audio,
	AudioConfiguration,
	AurHelper,
	AurHelperConfiguration,
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
from archinstall.lib.translationhandler import tr
from archinstall.tui.menu_item import MenuItem, MenuItemGroup, MenuItemRole
from archinstall.tui.result import ResultType


class ApplicationMenu(AbstractSubMenu[ApplicationConfiguration]):
	def __init__(
		self,
		preset: ApplicationConfiguration | None = None,
	):
		if preset:
			self._app_config = preset
		else:
			self._app_config = ApplicationConfiguration()

		menu_options = self._define_menu_options()
		self._item_group = MenuItemGroup(menu_options, checkmarks=True)

		super().__init__(
			self._item_group,
			config=self._app_config,
			allow_reset=True,
		)

	@override
	async def show(self) -> ApplicationConfiguration | None:
		_ = await super().show()
		return self._app_config

	def _define_menu_options(self) -> list[MenuItem]:
		return [
			MenuItem(text=tr('Hardware'), role=MenuItemRole.SECTION),
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
				preview_action=self._prev_firewall,
				key='firewall_config',
			),
			MenuItem(text=tr('Software'), role=MenuItemRole.SECTION),
			MenuItem(
				text=tr('AUR helper'),
				action=select_aur_helper,
				value=self._app_config.aur_helper_config,
				preview_action=self._prev_aur_helper,
				key='aur_helper_config',
			),
		]

	def _prev_power_management(self, item: MenuItem) -> str | None:
		if item.value is not None:
			config: PowerManagementConfiguration = item.value
			return f'{tr("Power management")}: {config.power_management.value}'
		return None

	def _prev_bluetooth(self, item: MenuItem) -> str | None:
		if item.value is not None:
			bluetooth_config: BluetoothConfiguration = item.value

			output = f'{tr("Bluetooth")}: '
			output += tr('Enabled') if bluetooth_config.enabled else tr('Disabled')
			return output
		return None

	def _prev_audio(self, item: MenuItem) -> str | None:
		if item.value is not None:
			config: AudioConfiguration = item.value
			return f'{tr("Audio")}: {config.audio.value}'
		return None

	def _prev_print_service(self, item: MenuItem) -> str | None:
		if item.value is not None:
			print_service_config: PrintServiceConfiguration = item.value

			output = f'{tr("Print service")}: '
			output += tr('Enabled') if print_service_config.enabled else tr('Disabled')
			return output
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
			return f'{tr("Firewall")}: {config.firewall.value}'
		return None

	def _prev_fonts(self, item: MenuItem) -> str | None:
		if item.value is not None:
			config: FontsConfiguration = item.value
			packages = ', '.join(f.value for f in config.fonts)
			return f'{tr("Additional fonts")}: {packages}'
		return None

	def _prev_aur_helper(self, item: MenuItem) -> str | None:
		if item.value is not None:
			config: AurHelperConfiguration = item.value
			return f'{tr("AUR helper")}: {config.aur_helper.value}'
		return None


async def select_aur_helper(preset: AurHelperConfiguration | None = None) -> AurHelperConfiguration | None:
	group = MenuItemGroup.from_enum(AurHelper, sort_items=False)
	if preset:
		group.set_focus_by_value(preset.aur_helper)

	result = await Selection[AurHelper](
		group,
		header=tr(
			'Warning: AUR packages are community-maintained and can execute arbitrary build scripts. '
			'Review PKGBUILDs and install only software you trust. Select a helper to build and install it automatically.'
		)
		+ '\n',
		allow_skip=True,
		allow_reset=True,
		preview_location='right',
	).show()

	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Selection:
			return AurHelperConfiguration(result.get_value())
		case ResultType.Reset:
			return None


async def select_power_management(preset: PowerManagementConfiguration | None = None) -> PowerManagementConfiguration | None:
	group = MenuItemGroup.from_enum(PowerManagement)
	group.set_default_by_value(PowerManagement.POWER_PROFILES_DAEMON)

	if preset:
		group.set_focus_by_value(preset.power_management)
	else:
		group.set_focus_by_value(PowerManagement.POWER_PROFILES_DAEMON)

	result = await Selection[PowerManagement](
		group,
		allow_skip=True,
		allow_reset=True,
	).show()

	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Selection:
			return PowerManagementConfiguration(power_management=result.get_value())
		case ResultType.Reset:
			return None


async def select_bluetooth(preset: BluetoothConfiguration | None) -> BluetoothConfiguration | None:
	header = tr('Would you like to configure Bluetooth?') + '\n'

	result = await Confirmation(
		header=header,
		allow_skip=True,
	).show()

	match result.type_:
		case ResultType.Selection:
			return BluetoothConfiguration(result.get_value())
		case ResultType.Skip:
			return preset
		case _:
			raise ValueError('Unhandled result type')


async def select_print_service(preset: PrintServiceConfiguration | None) -> PrintServiceConfiguration | None:
	header = tr('Would you like to configure the print service?') + '\n'

	result = await Confirmation(
		header=header,
		allow_skip=True,
	).show()

	match result.type_:
		case ResultType.Selection:
			result.get_value()
			return PrintServiceConfiguration(result.get_value())
		case ResultType.Skip:
			return preset
		case _:
			raise ValueError('Unhandled result type')


async def select_audio(preset: AudioConfiguration | None = None) -> AudioConfiguration | None:
	items = [MenuItem(a.value, value=a) for a in Audio]
	group = MenuItemGroup(items)

	if preset:
		group.set_focus_by_value(preset.audio)

	result = await Selection[Audio](
		group,
		header=tr('Select audio configuration'),
		allow_skip=True,
	).show()

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

	if preset:
		group.set_focus_by_value(preset.firewall)
	else:
		group.set_focus_by_value(Firewall.FWD)

	result = await Selection[Firewall](
		group,
		allow_skip=True,
		allow_reset=True,
	).show()

	match result.type_:
		case ResultType.Skip:
			return preset
		case ResultType.Selection:
			return FirewallConfiguration(firewall=result.get_value())
		case ResultType.Reset:
			return None


async def select_fonts(preset: FontsConfiguration | None = None) -> FontsConfiguration | None:
	items = [MenuItem(f'{f.value} ({f.description()})', value=f) for f in FontPackage]
	group = MenuItemGroup(items)

	if preset:
		for f in preset.fonts:
			group.set_selected_by_value(f)

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
			if selected:
				return FontsConfiguration(fonts=selected)
			return None
		case ResultType.Reset:
			return None
