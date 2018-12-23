from typing import (
    Generator,
)
from reparser import (
    Segment,
    BaseParser,
)


def serialize(segments: 'Generator[Segment]'):
    return [(segment.text, segment.params) for segment in segments]


def get_segments(text: 'str', parser: 'BaseParser'):
    return serialize(parser.parse(text))
