import asyncio

from pytest import MonkeyPatch

from archinstall.lib.general.system_menu import select_kernel
from archinstall.lib.menu.helpers import Selection
from archinstall.lib.models.package_types import Kernel
from archinstall.tui.result import Result


def test_kernel_selection_returns_package_names(monkeypatch: MonkeyPatch) -> None:
	async def show(_selection: Selection[Kernel]) -> Result[Kernel]:
		return Result.selection([Kernel.LINUX, Kernel.LINUX_LTS])

	monkeypatch.setattr(Selection, 'show', show)
	assert asyncio.run(select_kernel(['linux'])) == ['linux', 'linux-lts']
