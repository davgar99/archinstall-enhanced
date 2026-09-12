from pathlib import Path

import pytest

import archinstall.lib.crypt as crypt


def test_search_login_defs_accepts_tab_separated_directive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
	login_defs = tmp_path / 'login.defs'
	login_defs.write_text('YESCRYPT_COST_FACTOR\t7\n')
	monkeypatch.setattr(crypt, 'LOGIN_DEFS', login_defs)

	assert crypt._search_login_defs('YESCRYPT_COST_FACTOR') == '7'


def test_search_login_defs_requires_exact_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
	login_defs = tmp_path / 'login.defs'
	login_defs.write_text('YESCRYPT_COST_FACTOR_OLD 9\nYESCRYPT_COST_FACTOR 5\n')
	monkeypatch.setattr(crypt, 'LOGIN_DEFS', login_defs)

	assert crypt._search_login_defs('YESCRYPT_COST_FACTOR') == '5'
