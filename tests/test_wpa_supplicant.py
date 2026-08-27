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
