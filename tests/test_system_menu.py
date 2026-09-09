import asyncio

import pytest
from pytest import MonkeyPatch

from archinstall.lib.general.system_menu import recommended_gfx_driver, select_kernel
from archinstall.lib.hardware import GfxDriver, SysInfo
from archinstall.lib.menu.helpers import Selection
from archinstall.lib.models.package_types import Kernel
from archinstall.tui.result import Result


def test_kernel_selection_returns_package_names(monkeypatch: MonkeyPatch) -> None:
	async def show(_selection: Selection[Kernel]) -> Result[Kernel]:
		return Result.selection([Kernel.LINUX, Kernel.LINUX_LTS])

	monkeypatch.setattr(Selection, 'show', show)
	assert asyncio.run(select_kernel(['linux'])) == ['linux', 'linux-lts']


@pytest.mark.parametrize(
	('amd', 'intel', 'nvidia', 'expected'),
	[
		(True, False, False, GfxDriver.AmdOpenSource),
		(False, True, False, GfxDriver.IntelOpenSource),
		(False, False, True, GfxDriver.NvidiaOpenKernel),
		(True, True, False, GfxDriver.AllOpenSource),
		(False, False, False, GfxDriver.AllOpenSource),
	],
)
def test_recommended_gfx_driver_matches_detected_hardware(
	monkeypatch: MonkeyPatch,
	amd: bool,
	intel: bool,
	nvidia: bool,
	expected: GfxDriver,
) -> None:
	monkeypatch.setattr(SysInfo, 'virtualization', lambda: None)
	monkeypatch.setattr(SysInfo, 'has_amd_graphics', lambda: amd)
	monkeypatch.setattr(SysInfo, 'has_intel_graphics', lambda: intel)
	monkeypatch.setattr(SysInfo, 'has_nvidia_graphics', lambda: nvidia)

	assert recommended_gfx_driver() == expected


def test_recommended_gfx_driver_detects_virtualbox(monkeypatch: MonkeyPatch) -> None:
	monkeypatch.setattr(SysInfo, 'virtualization', lambda: 'oracle')

	assert recommended_gfx_driver() == GfxDriver.VMOpenSource
