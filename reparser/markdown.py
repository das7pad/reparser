"""Markdown Parser"""

import abc
import re
from typing import (  # pylint:disable=unused-import
    List,
    Match,
    Union,
    Tuple,
)
from reparser import (
    BaseParser,
    MatchType,
    Parser,
    Token,
)
from reparser import (  # typing: pylint:disable=unused-import
    TokenStack,
)


B_LEFT = r'(?:(?<=[^a-zA-Z0-9])|(?<=^))'
B_RIGHT = r'(?:(?=[^a-zA-Z0-9])|(?=$))'

MARKDOWN_COMMON_END = r'(?<![\s\\])({tokens})' + B_RIGHT
MARKDOWN_COMMON_START = (
    B_LEFT +
    r'(?<!\\)(?P<tag>{tokens})'
    r'(?!\s)(?:(?!(?P=tag)))'
    r'(?=.+?(?:(?<![\s\\]))(?P=tag)%s)'
    % B_RIGHT
)
MARKDOWN_SKIP_END = r'(?<!\\)({tokens})'
MARKDOWN_SKIP_START = (
    r'(?<!\\)(?P<skip_tag>{tokens})'
    r'(?:(?!(?P=skip_tag)))'
    r'(?=.+?(?:(?<!\\))(?P=skip_tag))'
)
RE_CLEAN_WHITESPACE = re.compile(' +')


class MarkdownTag:
    """Container for a single markdown tag"""
    def __init__(
        self,
        char: 'str',
        skip: 'bool' = False,
        **params
    ):
        self.char = char
        self.skip = skip
        self.params = params


class MarkdownGroup(Token):
    """Container for a markdown tags that can be used as token for the parser"""
    def __init__(
        self,
        *tokens: 'MarkdownTag',
        name: 'str' = 'markdown',
        **params
    ):
        self.__tokens = {}
        for token in tokens:
            self.__tokens[token.char.replace(r'\*', '*')] = token

        common_tokens = '|'.join(
            token.char for token in tokens
            if not token.skip
        )
        skip_tokens = '|'.join(
            token.char for token in tokens
            if token.skip
        )

        pattern_start = []
        pattern_end = []

        if common_tokens:
            pattern_start.append(
                MARKDOWN_COMMON_START.format(
                    tokens=common_tokens,
                )
            )
            pattern_end.append(
                MARKDOWN_COMMON_END.format(
                    tokens=common_tokens,
                )
            )

        if skip_tokens:
            pattern_start.append(
                MARKDOWN_SKIP_START.format(
                    tokens=skip_tokens,
                )
            )
            pattern_end.append(
                MARKDOWN_SKIP_END.format(
                    tokens=skip_tokens,
                )
            )

        super().__init__(
            name=name,
            pattern_start='|'.join(pattern_start),
            pattern_end='|'.join(pattern_end),
            **params
        )

    def get_tag(
        self,
        char: 'str'
    ) -> 'MarkdownTag':
        """Provide access on the markdown char to markdown tag mapping"""
        return self.__tokens[char]


class MarkdownBaseParser(BaseParser, metaclass=abc.ABCMeta):
    """Simple Markdown parser"""

    # this is an intermediate ABC which has neither pre- nor postprocessing
    # pylint:disable=abstract-method

    def __init__(
        self,
        tokens: 'List[Union[Token, MarkdownGroup, MarkdownTag]]',
    ):
        tags_to_wrap = []
        final_tokens = []
        names = []
        for mixed in tokens:
            if isinstance(mixed, MarkdownTag):
                tags_to_wrap.append(mixed)
                continue
            if isinstance(mixed, MarkdownGroup):
                names.append(mixed.name)
            final_tokens.append(mixed)

        if tags_to_wrap:
            unique_name = 'markdown'
            while unique_name in names:
                unique_name += 'G'
            final_tokens.append(
                MarkdownGroup(
                    *tags_to_wrap,
                    name=unique_name,
                )
            )

        super().__init__(
            tokens=final_tokens,
        )

    def get_matched_token(
        self,
        match: 'Match',
        token_stack: 'TokenStack',
    ) -> 'Tuple[Union[Token, MarkdownTag], MatchType, str]':
        """map a matched markdown group on its matched markdown tag"""
        markdown_group, match_type, group = super().get_matched_token(
            match=match,
            token_stack=token_stack,
        )

        if not isinstance(markdown_group, MarkdownGroup):
            return markdown_group, match_type, group

        char = match.group(0)
        markdown_tag = markdown_group.get_tag(char)

        if markdown_tag.skip:
            try:
                last_tag = token_stack.get_last_token()
            except IndexError:
                pass
            else:
                if last_tag is markdown_tag:
                    match_type = MatchType.end

        return markdown_tag, match_type, group


class MarkdownParser(Parser, MarkdownBaseParser):
    """Markdown parser with postprocessing"""

    def postprocess(
        self,
        text: 'str',
    )-> 'str':
        return RE_CLEAN_WHITESPACE.sub(' ', text)
