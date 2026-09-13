from pathlib import Path

from archinstall.applications.graphics_extras import GraphicsExtrasApp
from archinstall.lib.hardware import GfxDriver


class FakeInstaller:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.kernels = ['linux', 'linux-lts']
		self.packages: list[str] = []

	def add_additional_packages(self, packages: str | list[str]) -> None:
		if isinstance(packages, str):
			self.packages.append(packages)
		else:
			self.packages.extend(packages)


def test_nvidia_dkms_installs_matching_kernel_headers(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	GraphicsExtrasApp().install(installer, False, False, GfxDriver.NvidiaOpenKernel)  # type: ignore[arg-type]

	assert installer.packages == ['linux-headers', 'linux-lts-headers']
