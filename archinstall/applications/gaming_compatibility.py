from typing import TYPE_CHECKING

from archinstall.lib.models.gaming import GamingConfiguration

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


class GamingCompatibilityApp:
	VM_MAX_MAP_COUNT = 2147483642

	def install(self, install_session: Installer, gaming_config: GamingConfiguration) -> None:
		if gaming_config.increase_vm_max_map_count is not True:
			return

		config_path = install_session.target / 'etc/sysctl.d/80-gamecompatibility.conf'
		config_path.parent.mkdir(parents=True, exist_ok=True)
		config_path.write_text(
			'# Improve compatibility for memory-map-heavy games under Wine/Proton.\n'
			'# Matches the optional SteamOS-compatible value documented by ArchWiki.\n'
			f'vm.max_map_count = {self.VM_MAX_MAP_COUNT}\n'
		)
