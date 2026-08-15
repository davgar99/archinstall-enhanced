from dataclasses import dataclass
from typing import NotRequired, Self, TypedDict, override

from archinstall.lib.models.config import SubConfig
from archinstall.lib.translationhandler import tr


class PacmanConfigSerialization(TypedDict):
	parallel_downloads: int
	color: bool
	ilove_candy: NotRequired[bool]


@dataclass
class PacmanConfiguration(SubConfig):
	parallel_downloads: int = 5
	color: bool = True
	ilove_candy: bool = False

	@override
	def json(self) -> PacmanConfigSerialization:
		return {
			'parallel_downloads': self.parallel_downloads,
			'color': self.color,
			'ilove_candy': self.ilove_candy,
		}

	@override
	def summary(self) -> list[str]:
		color_status = tr('Enabled') if self.color else tr('Disabled')
		candy_status = tr('Enabled') if self.ilove_candy else tr('Disabled')
		return [
			f'{tr("Parallel Downloads")}: {self.parallel_downloads}',
			f'{tr("Color")}: {color_status}',
			f'{tr("ILoveCandy")}: {candy_status}',
		]

	def preview(self) -> str:
		color_str = tr('Enabled') if self.color else tr('Disabled')
		candy_str = tr('Enabled') if self.ilove_candy else tr('Disabled')
		output = '{}: {}\n'.format(tr('Parallel Downloads'), self.parallel_downloads)
		output += '{}: {}\n'.format(tr('Color'), color_str)
		output += '{}: {}'.format(tr('ILoveCandy'), candy_str)
		return output

	@classmethod
	def parse_arg(cls, args: PacmanConfigSerialization) -> Self:
		config = cls()

		if 'parallel_downloads' in args:
			config.parallel_downloads = int(args['parallel_downloads'])
		if 'color' in args:
			config.color = bool(args['color'])
		if 'ilove_candy' in args:
			config.ilove_candy = bool(args['ilove_candy'])

		return config
