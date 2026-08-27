import asyncio

from rich.text import Text
from textual.app import App
from textual.widgets import Footer, Input, Label, OptionList

from archinstall.tui.components import OptionListScreen, _AppInstance
from archinstall.tui.menu_item import MenuItem, MenuItemGroup, MenuItemRole, MenuItemState


class _PresentationApp(App[None]):
	CSS = _AppInstance.CSS


def _prompt(options: OptionList, index: int) -> Text:
	value = options.get_option_at_index(index).prompt
	assert isinstance(value, Text)
	return value


def test_master_layout_header_sections_preview_and_footer_at_supported_sizes() -> None:
	async def exercise(size: tuple[int, int]) -> None:
		app = _PresentationApp()
		items = [
			MenuItem('Global', role=MenuItemRole.SECTION, space_before=False),
			MenuItem('Disk configuration', state=MenuItemState.BLOCKING, preview_action=lambda _item: 'Disk details'),
			MenuItem('Applications', role=MenuItemRole.SECTION),
			MenuItem('Audio'),
			MenuItem('Gaming', role=MenuItemRole.SECTION),
			MenuItem('GameMode'),
			MenuItem('Actions', role=MenuItemRole.SECTION),
			MenuItem('Save configuration', role=MenuItemRole.ACTION),
			MenuItem('Install', role=MenuItemRole.ACTION),
			MenuItem('Abort', role=MenuItemRole.ACTION),
		]
		screen: OptionListScreen[int] = OptionListScreen(
			MenuItemGroup(items),
			title='Archinstall Enhanced',
			preview_location='right',
			enable_filter=True,
		)
		async with app.run_test(size=size) as pilot:
			await app.push_screen(screen)
			await pilot.pause()
			options = screen.query_one(OptionList)
			header = screen.query_one('.app-header', Label)
			assert str(header.render()) == 'Archinstall Enhanced'
			assert str(header.styles.background) == 'Color(0, 0, 255)'
			assert options.region.width > 0
			assert screen.query_one('#preview_content', Label).region.x >= options.region.right
			assert screen.query_one(Footer).display
			assert _prompt(options, 0).plain == 'Global'
			assert _prompt(options, 2).plain == '\nApplications'
			assert _prompt(options, 4).plain == '\nGaming'
			assert _prompt(options, 6).plain == '\nActions'
			assert [_prompt(options, index).plain for index in range(7, 10)] == [
				'    Save configuration',
				'    Install',
				'    Abort',
			]
			assert _prompt(options, 1).plain == '! Disk configuration'
			assert 'bright_yellow' in str(_prompt(options, 1).spans[0].style)

	for size in ((160, 50), (100, 30), (80, 24)):
		asyncio.run(exercise(size))


def test_filter_updates_preview_and_recovers_focus() -> None:
	async def exercise() -> None:
		app = _PresentationApp()
		group = MenuItemGroup(
			[
				MenuItem('Alpha', value=1, preview_action=lambda _item: 'Alpha preview'),
				MenuItem('Beta', value=2, preview_action=lambda _item: 'Beta preview'),
			]
		)
		screen: OptionListScreen[int] = OptionListScreen(group, preview_location='right', enable_filter=True)
		async with app.run_test(size=(80, 24)) as pilot:
			await app.push_screen(screen)
			await pilot.pause()
			field = screen.query_one(Input)
			field.focus()
			await pilot.press('z', 'z', 'z')
			await pilot.pause()
			assert screen.query_one(OptionList).option_count == 0
			assert 'No matching options' in str(screen.query_one('#preview_content', Label).render())
			field.value = ''
			await pilot.pause()
			assert screen.query_one(OptionList).option_count == 2
			assert group.focus_item is not None

	asyncio.run(exercise())


def test_scrolling_long_translation_keeps_footer_visible() -> None:
	async def exercise(size: tuple[int, int]) -> None:
		app = _PresentationApp()
		items = [MenuItem('First section with a deliberately long translated subtitle', role=MenuItemRole.SECTION)]
		items.extend(MenuItem(f'Scrolling option {index}') for index in range(90))
		screen: OptionListScreen[int] = OptionListScreen(MenuItemGroup(items), title='Archinstall Enhanced', preview_location='right')
		async with app.run_test(size=size) as pilot:
			await app.push_screen(screen)
			await pilot.pause()
			options = screen.query_one(OptionList)
			await pilot.press(*(['down'] * 88))
			await pilot.pause()
			assert options.scroll_offset.y > 0
			assert options.highlighted == 89
			assert screen.query_one(Footer).display

	for size in ((160, 50), (100, 30), (80, 24)):
		asyncio.run(exercise(size))
