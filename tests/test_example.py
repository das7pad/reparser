import re
from reparser import (
    Parser,
    Token,
    MatchGroup,
)

from .common import (
    get_segments,
)
from .data import (
    MARKDOWN_TEXT_EXAMPLE,
    MARKDOWN_SERIALIZED_SEGMENTS_EXAMPLE,
)


def get_parser():
    boundary_chars = r'\s`!()\[\]{{}};:\'".,<>?«»“”‘’*_~='
    b_left = r'(?:(?<=[' + boundary_chars + r'])|(?<=^))'  # Lookbehind
    b_right = r'(?:(?=[' + boundary_chars + r'])|(?=$))'   # Lookahead

    markdown_start = b_left + r'(?<!\\){tag}(?!\s)(?!{tag})'
    markdown_end = r'(?<!{tag})(?<!\s)(?<!\\){tag}' + b_right
    markdown_link = r'(?<!\\)\[(?P<link>.+?)\]\((?P<url>.+?)\)'
    newline = r'\n|\r\n'

    url_proto_regex = re.compile(r'(?i)^[a-z][\w-]+:/{1,3}')

    def markdown(tag):
        """Return sequence of start and end regex patterns for a Markdown tag"""
        return markdown_start.format(tag=tag), markdown_end.format(tag=tag)

    def url_complete(url):
        """If URL doesn't start with protocol, prepend it with http://"""
        return url if url_proto_regex.search(url) else 'http://' + url

    tokens = [
        Token('bi1',  *markdown(r'\*\*\*'), is_bold=True, is_italic=True),
        Token('bi2',  *markdown(r'___'),    is_bold=True, is_italic=True),
        Token('b1',   *markdown(r'\*\*'),   is_bold=True),
        Token('b2',   *markdown(r'__'),     is_bold=True),
        Token('i1',   *markdown(r'\*'),     is_italic=True),
        Token('i2',   *markdown(r'_'),      is_italic=True),
        Token('s',    *markdown(r'~~'),     is_strikethrough=True),
        Token('u',    *markdown(r'=='),     is_underline=True),
        Token('link', markdown_link, text=MatchGroup('link'),
              link_target=MatchGroup('url', func=url_complete)),
        Token('br', newline, text='\n', segment_type="LINE_BREAK")
    ]

    return Parser(tokens)


def test_example():
    actual = get_segments(MARKDOWN_TEXT_EXAMPLE, get_parser())
    expected = MARKDOWN_SERIALIZED_SEGMENTS_EXAMPLE
    assert expected == actual
