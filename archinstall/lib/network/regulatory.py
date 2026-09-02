from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from archinstall.lib.hardware import SysInfo
from archinstall.lib.log import debug, warn

if TYPE_CHECKING:
	from archinstall.lib.installer import Installer


_ZONE_TABLE = Path('/usr/share/zoneinfo/zone1970.tab')


def country_code_for_timezone(timezone: str | None, zone_table: Path = _ZONE_TABLE) -> str | None:
	"""Return an unambiguous ISO 3166-1 alpha-2 code for an IANA timezone."""
	if not timezone or not zone_table.is_file():
		return None

	for line in zone_table.read_text(encoding='utf-8').splitlines():
		if not line or line.startswith('#'):
			continue
		fields = line.split('\t')
		if len(fields) < 3 or fields[2] != timezone:
			continue
		countries = fields[0].split(',')
		if len(countries) == 1 and len(countries[0]) == 2:
			return countries[0].upper()
		return None

	return None


def configure_wireless_regulatory(installation: Installer, timezone: str | None) -> None:
	"""Install and configure the Linux wireless regulatory database when Wi-Fi exists."""
	if not SysInfo.has_wifi():
		debug('No Wi-Fi hardware detected; skipping wireless regulatory database')
		return

	installation.add_additional_packages(['wireless-regdb', 'iw'])

	country = country_code_for_timezone(timezone)
	if country:
		debug(f'Configuring wireless regulatory domain {country} from timezone {timezone}')
	elif timezone:
		warn(f'Could not infer one country from timezone {timezone}; retaining the world regulatory domain')
	else:
		debug('No timezone configured; retaining the world regulatory domain until one is available')

	_configure_regdom_files(installation.target)
	installation.enable_service(['wireless-regdom.service', 'wireless-regdom.path'])


def _configure_regdom_files(target: Path) -> None:
	conf_dir = target / 'etc/conf.d'
	conf_dir.mkdir(parents=True, exist_ok=True)
	(conf_dir / 'wireless-regdom').write_text(
		'# Set this to an ISO 3166-1 alpha-2 country code to override timezone detection.\nWIRELESS_REGDOM=AUTO\n',
		encoding='utf-8',
	)

	script_dir = target / 'usr/lib/archinstall'
	script_dir.mkdir(parents=True, exist_ok=True)
	script = script_dir / 'set-wireless-regdom'
	script.write_text(
		"""#!/bin/sh
set -eu

config=${WIRELESS_REGDOM_CONFIG:-/etc/conf.d/wireless-regdom}
timedatectl_command=${WIRELESS_REGDOM_TIMEDATECTL:-/usr/bin/timedatectl}
zone_table=${WIRELESS_REGDOM_ZONE_TABLE:-/usr/share/zoneinfo/zone1970.tab}
iw_command=${WIRELESS_REGDOM_IW:-/usr/bin/iw}
regdom=AUTO
if [ -r "$config" ]; then
	. "$config"
	regdom="${WIRELESS_REGDOM:-AUTO}"
fi

if [ "$regdom" = AUTO ]; then
	timezone=$("$timedatectl_command" show --property=Timezone --value 2>/dev/null || true)
	regdom=$(awk -F '\t' -v zone="$timezone" '
		$0 !~ /^#/ && $3 == zone && $1 !~ /,/ && length($1) == 2 {
			print toupper($1)
			exit
		}
	' "$zone_table")
fi

case "$regdom" in
	[A-Z][A-Z]) exec "$iw_command" reg set "$regdom" ;;
	*) exit 0 ;;
esac
""",
		encoding='utf-8',
	)
	script.chmod(0o755)

	systemd_dir = target / 'etc/systemd/system'
	systemd_dir.mkdir(parents=True, exist_ok=True)
	(systemd_dir / 'wireless-regdom.service').write_text(
		"""[Unit]
Description=Set wireless regulatory domain from the system timezone
Documentation=https://wiki.archlinux.org/title/Network_configuration/Wireless
After=local-fs.target
ConditionPathExists=/usr/share/zoneinfo/zone1970.tab

[Service]
Type=oneshot
ExecStart=/usr/lib/archinstall/set-wireless-regdom

[Install]
WantedBy=multi-user.target
""",
		encoding='utf-8',
	)
	(systemd_dir / 'wireless-regdom.path').write_text(
		"""[Unit]
Description=Update wireless regulatory domain when the timezone changes

[Path]
PathChanged=/etc/localtime
Unit=wireless-regdom.service

[Install]
WantedBy=multi-user.target
""",
		encoding='utf-8',
	)
