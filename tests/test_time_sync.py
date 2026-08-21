from unittest.mock import MagicMock

from archinstall.lib.installer import Installer


def test_activate_time_synchronization_enables_sync_services() -> None:
	installer = MagicMock(spec=Installer)

	Installer.activate_time_synchronization(installer)

	installer.enable_service.assert_called_once_with(
		['systemd-timesyncd.service', 'systemd-time-wait-sync.service'],
	)
