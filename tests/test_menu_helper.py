from dataclasses import dataclass

from archinstall.lib.menu.menu_helper import MenuHelper


@dataclass
class TableEntry:
	value: str

	def table_data(self) -> dict[str, str]:
		return {'Value': self.value}


def test_table_mapping_ignores_trailing_table_newline() -> None:
	data = [TableEntry('alice'), TableEntry('bob')]
	mapping = MenuHelper(data)._table_to_data_mapping(data)

	assert list(mapping.values())[2:] == data
	assert '' not in mapping
