"""Test the Markdown Parser"""

import re
from reparser import (
    Token,
    MatchGroup,
)

from reparser.markdown import (
    MarkdownParser,
    MarkdownTag,
)

from .common import (
    get_segments,
)
from .data import (
    MARKDOWN_TEXT_EXAMPLE,
    MARKDOWN_SERIALIZED_SEGMENTS_EXAMPLE,
)


def get_parser():
    markdown_link = r'(?<!\\)\[(?P<link>.+?)\]\((?P<url>.+?)\)'
    newline = r'\n|\r\n'
    url_proto_regex = re.compile(r'(?i)^[a-z][\w-]+:/{1,3}')

    def url_complete(url):
        """If URL doesn't start with protocol, prepend it with http://"""
        return url if url_proto_regex.search(url) else 'http://' + url

    tokens = [
        MarkdownTag(r'\*\*\*',  is_bold=True, is_italic=True),
        MarkdownTag(r'___',     is_bold=True, is_italic=True),
        MarkdownTag(r'\*\*',    is_bold=True),
        MarkdownTag(r'__',      is_bold=True),
        MarkdownTag(r'\*',      is_italic=True),
        MarkdownTag(r'_',       is_italic=True),
        MarkdownTag(r'```',     skip=True),
        MarkdownTag(r'``',      skip=True),
        MarkdownTag(r'`',       skip=True),
        MarkdownTag(r'~~',      is_strikethrough=True),
        MarkdownTag(r'==',      is_underline=True),
        Token('link', markdown_link, text=MatchGroup('link'),
              link_target=MatchGroup('url', func=url_complete)),
        Token('br', newline, text='\n', segment_type="LINE_BREAK")
    ]

    return MarkdownParser(tokens)


def test_single_bold():
    parser = MarkdownParser([
        MarkdownTag(r'\*\*', is_bold=True),
    ])
    text = 'pre **BOLD** post'
    expected = [
        ('pre ', {}),
        ('BOLD', {'is_bold': True}),
        (' post', {}),
    ]
    actual = get_segments(text, parser)

    assert expected == actual


def test_whitespace():
    parser = MarkdownParser([
        MarkdownTag(r'\*\*', is_bold=True),
    ])
    text = 'pre  **BOLD  TEXT**  post'
    expected = [
        ('pre ', {}),
        ('BOLD TEXT', {'is_bold': True}),
        (' post', {}),
    ]
    actual = get_segments(text, parser)

    assert expected == actual


def test_single_skip():
    parser = MarkdownParser([
        MarkdownTag(r'\*', is_bold=True),
        MarkdownTag(r'`', skip=True),
    ])
    text = 'pre `*skip*` post'
    expected = [
        ('pre ', {}),
        ('*skip*', {}),
        (' post', {}),
    ]
    actual = get_segments(text, parser)

    assert expected == actual


def test_whitespace_skip():
    parser = MarkdownParser([
        MarkdownTag(r'\*', is_bold=True),
        MarkdownTag(r'`', skip=True),
    ])
    text = 'pre `*skip  this*` post'
    expected = [
        ('pre ', {}),
        ('*skip  this*', {}),
        (' post', {}),
    ]
    actual = get_segments(text, parser)

    assert expected == actual


def test_example():
    actual = get_segments(MARKDOWN_TEXT_EXAMPLE, get_parser())
    expected = MARKDOWN_SERIALIZED_SEGMENTS_EXAMPLE
    assert expected == actual


def test_all_markdown_token():
    text = '\n'.join([
        '***bold italic***',
        '___bold italic___',
        '__bold__',
        '**bold**',
        '~~strike~~',
        '==underline==',
        '*italic*',
        '_italic_',
        '`skip`',
        '`*skip*`',
        '``**skip**``',
        '```***skip***```',
        '*mixed **formatting** demo*',
        '`*mixed **formatting** demo*`',
    ])

    actual = get_segments(text, get_parser())
    expected = [
        ('bold italic', {'is_bold': True, 'is_italic': True}),
        ('\n', {'segment_type': 'LINE_BREAK'}),
        ('bold italic', {'is_bold': True, 'is_italic': True}),
        ('\n', {'segment_type': 'LINE_BREAK'}),
        ('bold', {'is_bold': True}),
        ('\n', {'segment_type': 'LINE_BREAK'}),
        ('bold', {'is_bold': True}),
        ('\n', {'segment_type': 'LINE_BREAK'}),
        ('strike', {'is_strikethrough': True}),
        ('\n', {'segment_type': 'LINE_BREAK'}),
        ('underline', {'is_underline': True}),
        ('\n', {'segment_type': 'LINE_BREAK'}),
        ('italic', {'is_italic': True}),
        ('\n', {'segment_type': 'LINE_BREAK'}),
        ('italic', {'is_italic': True}),
        ('\n', {'segment_type': 'LINE_BREAK'}),
        ('skip', {}),
        ('\n', {'segment_type': 'LINE_BREAK'}),
        ('*skip*', {}),
        ('\n', {'segment_type': 'LINE_BREAK'}),
        ('**skip**', {}),
        ('\n', {'segment_type': 'LINE_BREAK'}),
        ('***skip***', {}),
        ('\n', {'segment_type': 'LINE_BREAK'}),
        ('mixed ', {'is_italic': True}),
        ('formatting', {'is_bold': True, 'is_italic': True}),
        (' demo', {'is_italic': True}),
        ('\n', {'segment_type': 'LINE_BREAK'}),
        ('*mixed **formatting** demo*', {}),
    ]
    assert expected == actual


def test_skipping():
    text = ('Hello `**not bold**` world!\n'
            'You can **try `*this*` awesome** `[link](www.eff.org)`.')

    actual = get_segments(text, get_parser())
    expected = [
        ('Hello ', {}),
        ('**not bold**', {}),
        (' world!', {}),
        ('\n', {'segment_type': 'LINE_BREAK'}),
        ('You can ', {}),
        ('try ', {'is_bold': True}),
        ('*this*', {'is_bold': True}),
        (' awesome', {'is_bold': True}),
        (' ', {}),
        ('[link](www.eff.org)', {}),
        ('.', {})
    ]
    assert expected == actual
