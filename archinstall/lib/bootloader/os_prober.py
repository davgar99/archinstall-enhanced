from __future__ import annotations

import re
from typing import TYPE_CHECKING

from archinstall.lib.log import debug, warn
from archinstall.lib.models.bootloader import Bootloader

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


_OS_PROBER_SETTING = re.compile(r'^\s*#?\s*GRUB_DISABLE_OS_PROBER\s*=.*$')


def enable_os_prober_in_grub_config(config: str) -> str:
	"""Return GRUB config content with os-prober enabled exactly once."""
	lines = config.splitlines()
	out: list[str] = []
	setting_written = False

	for line in lines:
		if _OS_PROBER_SETTING.match(line):
			if not setting_written:
				out.append('GRUB_DISABLE_OS_PROBER=false')
				setting_written = True
			continue
		out.append(line)

	if not setting_written:
		out.append('GRUB_DISABLE_OS_PROBER=false')

	return '\n'.join(out) + '\n'


def prepare_grub_os_prober(installation: Installer, bootloader: Bootloader, enabled: bool) -> None:
	"""
	Prepare GRUB for os-prober before the normal bootloader installation runs.

	GRUB is installed here together with os-prober and fuse3 so /etc/default/grub
	exists before it is edited. The normal add_bootloader() flow then performs the
	final grub-mkconfig run with os-prober already enabled.
	"""
	if not enabled:
		return

	if not bootloader.has_os_prober_support():
		warn(f'Bootloader {bootloader.value} does not support os-prober; ignoring the option.')
		return

	debug('Preparing GRUB os-prober support')
	installation.pacman.strap(['grub', 'os-prober', 'fuse3'])

	grub_default = installation.target / 'etc/default/grub'
	config = grub_default.read_text()
	grub_default.write_text(enable_os_prober_in_grub_config(config))
