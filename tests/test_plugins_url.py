from pathlib import Path
from unittest.mock import MagicMock

import pytest

import archinstall.lib.plugins as plugin_module


def test_local_plugin_loader_does_not_download_urls(monkeypatch: pytest.MonkeyPatch) -> None:
	download = MagicMock()
	monkeypatch.setattr(plugin_module, '_download_plugin_url', download)

	plugin_module.load_plugin('https://example.com/plugin.py')

	download.assert_not_called()


def test_remote_plugin_loader_rejects_plain_http(monkeypatch: pytest.MonkeyPatch) -> None:
	open_url = MagicMock()
	monkeypatch.setattr(plugin_module, 'urlopen', open_url)

	with pytest.raises(ValueError, match='HTTPS'):
		plugin_module._download_plugin_url('http://example.com/plugin.py')

	open_url.assert_not_called()


def test_remote_plugin_loader_rejects_non_network_urls() -> None:
	with pytest.raises(ValueError, match='HTTPS'):
		plugin_module._download_plugin_url('file:///tmp/plugin.py')


def test_explicit_remote_plugin_loader_cleans_up(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
	temporary = tmp_path / 'plugin.py'
	temporary.write_text('class Plugin:\n\tpass\n')

	download = MagicMock(return_value=temporary)
	load_local = MagicMock()
	monkeypatch.setattr(plugin_module, '_download_plugin_url', download)
	monkeypatch.setattr(plugin_module, 'load_plugin', load_local)

	plugin_module.load_plugin_url('https://example.com/plugin.py')

	download.assert_called_once_with('https://example.com/plugin.py')
	load_local.assert_called_once_with(temporary)
	assert not temporary.exists()
