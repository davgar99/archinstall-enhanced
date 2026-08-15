from typing import TYPE_CHECKING

from archinstall.lib.log import debug
from archinstall.lib.models.gaming import CPUSchedulerConfiguration

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


class CPUSchedulerApp:
	@property
	def packages(self) -> list[str]:
		return ['scx-scheds', 'scx-tools']

	def install(self, install_session: Installer, scheduler_config: CPUSchedulerConfiguration) -> None:
		scheduler = scheduler_config.scheduler
		debug(f'Installing sched-ext CPU scheduler: {scheduler.value}')

		install_session.add_additional_packages(self.packages)

		config_dir = install_session.target / 'etc/scx_loader'
		config_dir.mkdir(parents=True, exist_ok=True)

		config_path = config_dir / 'config.toml'
		config_path.write_text(f'default_sched = "{scheduler.value}"\ndefault_mode = "Gaming"\n')
		config_path.chmod(0o644)

		install_session.enable_service('scx_loader.service')
