import re
from pathlib import Path


def ensure_grub_pkgdatadir(script: Path) -> bool:
	"""Repair a GRUB generator script that references pkgdatadir without defining it."""
	if not script.exists():
		return False

	content = script.read_text()
	if 'grub-mkconfig_lib' not in content:
		return False
	if re.search(r'^\s*pkgdatadir=', content, flags=re.MULTILINE):
		return False

	datarootdir = re.search(r'^(?P<line>\s*datarootdir=.*)$', content, flags=re.MULTILINE)
	if datarootdir is None:
		return False

	insertion = '\npkgdatadir="${datarootdir}/grub"'
	content = content[: datarootdir.end()] + insertion + content[datarootdir.end() :]
	script.write_text(content)
	return True
