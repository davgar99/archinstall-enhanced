import importlib.util
import os
import sys
import tempfile
import urllib.error
import urllib.parse
from importlib import metadata
from pathlib import Path
from urllib.request import Request, urlopen

from archinstall.lib.log import error, info, warn
from archinstall.lib.version import get_version

plugins = {}


# 1: List archinstall.plugin definitions
# 2: Load the plugin entrypoint
# 3: Initiate the plugin and store it as .name in plugins
for plugin_definition in metadata.entry_points().select(group='archinstall.plugin'):
	plugin_entrypoint = plugin_definition.load()

	try:
		plugins[plugin_definition.name] = plugin_entrypoint()
	except Exception as err:
		error(
			f'Error: {err}',
			f'The above error was detected when loading the plugin: {plugin_definition}',
		)


# @archinstall.plugin decorator hook to programmatically add
# plugins in runtime. Useful in profiles_bck and other things.
def plugin(f, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
	plugins[f.__name__] = f


def _import_via_path(path: Path, namespace: str | None = None) -> str | None:
	if not namespace:
		namespace = os.path.basename(path)

		if namespace == '__init__.py':
			namespace = path.parent.name

	try:
		spec = importlib.util.spec_from_file_location(namespace, path)
		if spec and spec.loader:
			imported = importlib.util.module_from_spec(spec)
			sys.modules[namespace] = imported
			spec.loader.exec_module(sys.modules[namespace])
			return namespace
	except Exception as err:
		error(
			f'Error: {err}',
			f'The above error was detected when loading the plugin: {path}',
		)

		try:
			del sys.modules[namespace]
		except Exception:
			pass

	return None


def _download_plugin_url(url: str) -> Path:
	parsed = urllib.parse.urlparse(url)
	if parsed.scheme != 'https' or not parsed.netloc:
		raise ValueError('Plugin URL must use HTTPS and include a host')

	req = Request(url, headers={'User-Agent': 'ArchInstall'})
	try:
		# B310 is intentionally suppressed only after requiring an explicit HTTPS URL.
		with urlopen(req, timeout=30) as response:  # nosec B310
			data = response.read()
	except (urllib.error.URLError, TimeoutError) as err:
		raise ValueError(f'Could not download plugin from {url}: {err}') from err

	if not data.strip():
		raise ValueError(f'Downloaded plugin from {url} is empty')

	with tempfile.NamedTemporaryFile(prefix='archinstall_plugin_', suffix='.py', delete=False) as temp_file:
		temp_file.write(data)
		return Path(temp_file.name)


def load_plugin(path: Path | str) -> None:
	local_path = Path(path)
	info(f'Loading plugin from {local_path}')

	if not local_path.is_file():
		warn(f"Plugin '{path}' does not exist or is not a regular file.")
		return

	namespace = _import_via_path(local_path)
	if namespace is None or namespace not in sys.modules:
		return

	# Version dependency via __archinstall__version__ variable (if present) in the plugin
	version = get_version()
	if hasattr(sys.modules[namespace], '__archinstall__version__'):
		version_major_and_minor = version.rsplit('.', 1)[0]
		if sys.modules[namespace].__archinstall__version__ < float(version_major_and_minor):
			error(f'Plugin {sys.modules[namespace]} does not support the current Archinstall version.')

	if hasattr(sys.modules[namespace], 'Plugin'):
		try:
			plugins[namespace] = sys.modules[namespace].Plugin()
			info(f'Plugin {plugins[namespace]} has been loaded.')
		except Exception as err:
			error(
				f'Error: {err}',
				f'The above error was detected when initiating the plugin: {path}',
			)
	else:
		warn(f"Plugin '{path}' is missing a valid entry-point or is corrupt.")


def load_plugin_url(url: str) -> None:
	"""Download and execute a plugin only through the explicit HTTPS URL path."""
	temporary_path = _download_plugin_url(url)
	try:
		load_plugin(temporary_path)
	finally:
		temporary_path.unlink(missing_ok=True)
