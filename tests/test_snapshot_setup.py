from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from archinstall.lib.disk.snapshot_setup import _setup_snapper_config


def test_existing_snapshots_subvolume_is_registered_without_recreating(tmp_path: Path) -> None:
	(tmp_path / '.snapshots').mkdir()
	template = tmp_path / 'usr/share/snapper/config-templates/default'
	template.parent.mkdir(parents=True)
	template.write_text('SUBVOLUME="/old"\nFSTYPE="btrfs"\nTIMELINE_CREATE="yes"\n')

	installation = SimpleNamespace(target=tmp_path, arch_chroot=MagicMock())
	_setup_snapper_config(installation, 'root', Path('/'))  # type: ignore[arg-type]

	installation.arch_chroot.assert_not_called()
	config = (tmp_path / 'etc/snapper/configs/root').read_text()
	assert 'SUBVOLUME="/"' in config
	assert 'FSTYPE="btrfs"' in config
	assert 'root' in (tmp_path / 'etc/conf.d/snapper').read_text()
