from pathlib import Path

from archinstall.lib.grub import ensure_grub_pkgdatadir


def test_adds_missing_pkgdatadir(tmp_path: Path) -> None:
	script = tmp_path / '10_linux'
	script.write_text('prefix="/usr"\nexec_prefix="/usr"\ndatarootdir="/usr/share"\n. "$pkgdatadir/grub-mkconfig_lib"\n')

	assert ensure_grub_pkgdatadir(script) is True
	content = script.read_text()
	assert 'pkgdatadir="${datarootdir}/grub"' in content
	assert content.index('datarootdir=') < content.index('pkgdatadir=') < content.index('grub-mkconfig_lib')


def test_preserves_existing_pkgdatadir(tmp_path: Path) -> None:
	script = tmp_path / '10_linux'
	original = 'datarootdir="/usr/share"\npkgdatadir="/usr/share/grub"\n. "$pkgdatadir/grub-mkconfig_lib"\n'
	script.write_text(original)

	assert ensure_grub_pkgdatadir(script) is False
	assert script.read_text() == original


def test_ignores_unrelated_script(tmp_path: Path) -> None:
	script = tmp_path / '10_linux'
	original = 'datarootdir="/usr/share"\necho linux\n'
	script.write_text(original)

	assert ensure_grub_pkgdatadir(script) is False
	assert script.read_text() == original
