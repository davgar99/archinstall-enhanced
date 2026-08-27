import pytest

from archinstall.lib.utils.util import format_duration


@pytest.mark.parametrize(
	('seconds', 'expected'),
	[
		(0, '0s'),
		(5.4, '5s'),
		(45, '45s'),
		(60, '1m 00s'),
		(158, '2m 38s'),
		(599, '9m 59s'),
		(3600, '1h 00m 00s'),
		(3725, '1h 02m 05s'),
		(7384, '2h 03m 04s'),
		(-3, '0s'),
	],
)
def test_format_duration(seconds: float, expected: str) -> None:
	assert format_duration(seconds) == expected
