from archinstall.lib.network.network_menu import _validate_ip_input


def test_manual_interface_address_allows_prefix() -> None:
	assert _validate_ip_input('192.168.0.5/24', multi=False, allow_empty=False, allow_prefix=True) is None
	assert _validate_ip_input('2001:db8::5/64', multi=False, allow_empty=False, allow_prefix=True) is None


def test_gateway_rejects_network_prefix() -> None:
	assert _validate_ip_input('192.168.0.1', multi=False, allow_empty=True, allow_prefix=False) is None
	assert _validate_ip_input('192.168.0.1/24', multi=False, allow_empty=True, allow_prefix=False) is not None


def test_dns_servers_require_bare_addresses() -> None:
	assert (
		_validate_ip_input(
			'1.1.1.1 2606:4700:4700::1111',
			multi=True,
			allow_empty=True,
			allow_prefix=False,
		)
		is None
	)
	assert _validate_ip_input('1.1.1.1/32', multi=True, allow_empty=True, allow_prefix=False) is not None
