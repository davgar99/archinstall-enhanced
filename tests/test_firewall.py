import asyncio
from pathlib import Path
from typing import Any, cast

from pytest import MonkeyPatch

from archinstall.applications.firewall import FirewallApp
from archinstall.lib.applications.application_menu import select_firewall
from archinstall.lib.menu.helpers import Confirmation, Selection
from archinstall.lib.models.application import ApplicationConfiguration, Firewall, FirewallConfiguration
from archinstall.tui.result import Result


class FakeInstaller:
	def __init__(self, target: Path) -> None:
		self.target = target
		self.packages: list[str] = []
		self.services: list[str] = []
		self.commands: list[str] = []

	def add_additional_packages(self, packages: str | list[str]) -> None:
		self.packages.extend([packages] if isinstance(packages, str) else packages)

	def enable_service(self, services: str | list[str]) -> None:
		self.services.extend([services] if isinstance(services, str) else services)

	def arch_chroot(self, command: str) -> None:
		self.commands.append(command)


def test_firewall_menu_marks_recommended_and_focuses_first(monkeypatch: MonkeyPatch) -> None:
	async def select_focused(selection: Selection[Firewall]) -> Result[Firewall]:
		group = selection._group
		# The recommended option stays labelled with "(default)"...
		assert group.default_item is not None
		assert group.default_item.value == Firewall.FWD
		# ...but the cursor starts on the first option, consistent with every
		# other choice prompt.
		first = group.get_enabled_items()[0]
		assert group.focus_item is first
		return Result.selection(first.value)

	monkeypatch.setattr(Selection, 'show', select_focused)

	async def block_ssh(_confirmation: Confirmation) -> Result[bool]:
		return Result.false()

	monkeypatch.setattr(Confirmation, 'show', block_ssh)

	first_firewall = next(iter(Firewall))
	assert asyncio.run(select_firewall()) == FirewallConfiguration(first_firewall)


def test_firewall_menu_can_allow_ssh(monkeypatch: MonkeyPatch) -> None:
	async def select_firewalld(_selection: Selection[Firewall]) -> Result[Firewall]:
		return Result.selection(Firewall.FWD)

	async def allow_ssh(_confirmation: Confirmation) -> Result[bool]:
		return Result.true()

	monkeypatch.setattr(Selection, 'show', select_firewalld)
	monkeypatch.setattr(Confirmation, 'show', allow_ssh)

	assert asyncio.run(select_firewall()) == FirewallConfiguration(Firewall.FWD, allow_ssh=True)


def test_skipping_ssh_prompt_preserves_existing_choice(monkeypatch: MonkeyPatch) -> None:
	async def select_ufw(_selection: Selection[Firewall]) -> Result[Firewall]:
		return Result.selection(Firewall.UFW)

	async def skip_ssh(_confirmation: Confirmation) -> Result[bool]:
		return Result.skip()

	monkeypatch.setattr(Selection, 'show', select_ufw)
	monkeypatch.setattr(Confirmation, 'show', skip_ssh)
	preset = FirewallConfiguration(Firewall.FWD, allow_ssh=True)

	assert asyncio.run(select_firewall(preset)) == FirewallConfiguration(Firewall.UFW, allow_ssh=True)


def test_firewall_configuration_roundtrip_and_legacy_default() -> None:
	config = ApplicationConfiguration(firewall_config=FirewallConfiguration(Firewall.UFW, allow_ssh=True))
	assert ApplicationConfiguration.parse_arg(cast(dict[str, Any], config.json())) == config
	assert FirewallConfiguration.parse_arg({'firewall': 'ufw'}) == FirewallConfiguration(Firewall.UFW, allow_ssh=False)
	assert config.summary() == ['Firewall: ufw', 'Incoming SSH: Allowed']


def test_ufw_can_allow_ssh_before_first_boot(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	ufw_conf = tmp_path / 'etc/ufw/ufw.conf'
	ufw_conf.parent.mkdir(parents=True)
	ufw_conf.write_text('ENABLED=no\n')

	FirewallApp().install(installer, FirewallConfiguration(Firewall.UFW, allow_ssh=True))  # type: ignore[arg-type]

	assert installer.packages == ['ufw']
	assert installer.services == ['ufw.service']
	assert installer.commands == ['ufw allow 22/tcp']
	assert ufw_conf.read_text() == 'ENABLED=yes\n'


def test_firewalld_uses_offline_configuration_for_ssh(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)

	FirewallApp().install(installer, FirewallConfiguration(Firewall.FWD, allow_ssh=True))  # type: ignore[arg-type]

	assert installer.packages == ['firewalld']
	assert installer.services == ['firewalld.service']
	assert installer.commands == ['firewall-offline-cmd --add-service=ssh']


def test_firewall_leaves_ssh_closed_by_default(tmp_path: Path) -> None:
	installer = FakeInstaller(tmp_path)
	ufw_conf = tmp_path / 'etc/ufw/ufw.conf'
	ufw_conf.parent.mkdir(parents=True)
	ufw_conf.write_text('ENABLED=no\n')

	FirewallApp().install(installer, FirewallConfiguration(Firewall.UFW))  # type: ignore[arg-type]

	assert installer.commands == []
