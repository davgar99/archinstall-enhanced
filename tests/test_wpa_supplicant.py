from archinstall.lib.models.network import WifiNetwork
from archinstall.lib.network.wpa_supplicant import WpaSupplicantConfig, WpaSupplicantNetwork


def test_network_values_escape_quotes_and_newlines() -> None:
	config = WpaSupplicantConfig()
	network = WifiNetwork('aa:bb:cc:dd:ee:ff', '2412', '-40', '[WPA2]', 'Cafe"\nnetwork={')
	config.set_network(network, 'secret"\npriority=999')
	entry = config._wpa_networks[0]

	assert entry.ssid == network.ssid
	assert entry.psk == 'secret"\npriority=999'
	assert '\\n' in entry.to_config_entry()
	assert '\npriority=999' not in entry.to_config_entry()


def test_unquoted_hex_psk_remains_supported() -> None:
	psk = 'a' * 64
	entry = WpaSupplicantNetwork({'ssid': '"Home"', 'psk': psk})
	assert entry.psk == psk


def test_open_network_has_no_psk_and_uses_key_mgmt_none() -> None:
	config = WpaSupplicantConfig()
	network = WifiNetwork('aa:bb:cc:dd:ee:ff', '2412', '-40', '[ESS]', 'Cafe')

	config.set_network(network, None)
	entry = config._wpa_networks[0]

	assert entry.psk is None
	assert entry.mappings['key_mgmt'] == 'NONE'
	assert 'psk' not in entry.mappings


def test_existing_open_network_does_not_raise_for_missing_psk() -> None:
	entry = WpaSupplicantNetwork({'ssid': '"Cafe"', 'key_mgmt': 'NONE'})
	assert entry.psk is None


def test_incomplete_network_block_is_ignored_when_matching_ssid() -> None:
	config = WpaSupplicantConfig()
	config._wpa_networks = [WpaSupplicantNetwork({'key_mgmt': 'NONE'})]

	assert config.get_existing_network('Cafe') is None
