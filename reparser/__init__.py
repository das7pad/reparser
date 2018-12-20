"""Simple regex-based lexer/parser for inline markup"""

import enum
import re
from typing import (
    Callable,
    Dict,
    Generator,
    List,
    Match,
    Optional,
    Pattern,
    Tuple,
    Union,
)


# Precompiled regex for matching named groups in regex patterns
group_regex = re.compile(r'\?P<(.+?)>')


class Segment:
    """Segment of parsed text"""
    def __init__(
        self,
        text: 'Union[MatchGroup, str]',
        token: 'Optional[Token]' = None,
        match: 'Optional[Match]' = None,
        **params
    ):
        self.text = text
        self.params = params
        if token and match:
            self.update_text(token, match)
            self.update_params(token, match)

    def update_text(
        self,
        token: 'Token',
        match: 'Match',
    ):
        """Update text from results of regex match"""
        if isinstance(self.text, MatchGroup):
            self.text = self.text.get_group_value(token, match)

    def update_params(
        self,
        token: 'Token',
        match: 'Match',
    ):
        """Update dict of params from results of regex match"""
        for k, v in self.params.items():
            if isinstance(v, MatchGroup):
                self.params[k] = v.get_group_value(token, match)


class Token:
    """Definition of token which should be parsed from text"""
    def __init__(
        self,
        name: 'str',
        pattern_start: 'str',
        pattern_end: 'Optional[str]' = None,
        skip: 'Optional[bool]' = False,
        **params
    ):
        self.name = name
        self.group_start = '{}_start'.format(self.name)
        if not pattern_end:
            self.group_end = None
            self.pattern_start = self.modify_pattern(
                pattern=pattern_start,
                group=self.group_start,
            )
            self.pattern_end = None
        else:
            self.group_end = '{}_end'.format(self.name)
            self.pattern_start = self.modify_pattern(
                pattern=pattern_start + '(?=.+?%s)' % pattern_end,
                group=self.group_start,
            )
            self.pattern_end = self.modify_pattern(pattern_end, self.group_end)
        self.skip = skip
        self.params = params

    def modify_pattern(
        self,
        pattern: 'str',
        group: 'str',
    ) -> 'str':
        """Rename groups in regex pattern and enclose it in named group"""
        pattern = group_regex.sub(r'?P<{}_\1>'.format(self.name), pattern)
        return r'(?P<{}>{})'.format(group, pattern)


class MatchGroup:
    """Name of regex group which should be replaced by its value when token is parsed"""
    def __init__(
        self,
        group: 'str',
        func: 'Optional[Callable]' = None,
    ):
        self.group = group
        self.func = func

    def get_group_value(
        self,
        token: 'Token',
        match: 'Match',
    ) -> 'str':
        """Return value of regex match for the specified group"""
        try:
            value = match.group('{}_{}'.format(token.name, self.group))
        except IndexError:
            value = ''
        return self.func(value) if callable(self.func) else value


class MatchType(enum.Enum):
    """Type of token matched by regex"""
    start = 1
    end = 2
    single = 3


class Parser:
    """Simple regex-based lexer/parser for inline markup"""
    def __init__(
        self,
        tokens: 'List[Token]',
    ):
        self.tokens = tokens
        self.regex = self.build_regex(tokens)
        self.groups = self.build_groups(tokens)

    def preprocess(
        self,
        text: 'str',
    ) -> 'str':
        """Preprocess text before parsing (should be reimplemented by subclass)"""
        return text

    def postprocess(
        self,
        text: 'str',
    ) -> 'str':
        """Postprocess text after parsing (should be reimplemented by subclass)"""
        return text

    @staticmethod
    def build_regex(
        tokens: 'List[Token]',
    ) -> 'Pattern':
        """Build compound regex from list of tokens"""
        patterns = []
        for token in tokens:
            patterns.append(token.pattern_start)
            if token.pattern_end:
                patterns.append(token.pattern_end)
        return re.compile('|'.join(patterns), re.DOTALL)

    @staticmethod
    def build_groups(
        tokens: 'List[Token]',
    ) -> 'Dict[str, Tuple[Token, MatchType]]':
        """Build dict of groups from list of tokens"""
        groups = {}
        for token in tokens:
            if token.group_end:
                groups[token.group_start] = (token, MatchType.start)
                groups[token.group_end] = (token, MatchType.end)
            else:
                groups[token.group_start] = (token, MatchType.single)
        return groups

    def get_matched_token(
        self,
        match: 'Match',
    ) -> 'Tuple[Token, MatchType, str]':
        """Find which token has been matched by compound regex"""
        group = match.lastgroup
        token, match_type = self.groups[group]
        return token, match_type, group

    def get_params(
        self,
        token_stack: 'List[Token]',
    ) -> 'dict':
        """Get params from stack of tokens"""
        params = {}
        for token in token_stack:
            params.update(token.params)
        return params

    def remove_token(
        self,
        token_stack: 'List[Token]',
        token: 'Token',
    ) -> 'bool':
        """Remove last occurrence of token from stack"""
        if token_stack[-1] is token:
            token_stack.pop(-1)
            return True

        token_stack.reverse()
        try:
            token_stack.remove(token)
        except ValueError:
            return False
        else:
            return True
        finally:
            token_stack.reverse()

    def parse(
        self,
        text: 'str',
    ) -> 'Generator[Segment]':
        """Parse text to obtain list of Segments"""
        text = self.preprocess(text)
        token_stack = []
        last_pos = 0

        # Iterate through all matched tokens
        for match in self.regex.finditer(text):
            # Find which token has been matched by regex
            token, match_type, group = self.get_matched_token(match)

            # Get params from stack of tokens
            params = self.get_params(token_stack)

            # Should we skip interpreting tokens?
            skip = token_stack[-1].skip if token_stack else False

            # Check for end token first
            if match_type == MatchType.end:
                if not skip or token_stack[-1] == token:
                    removed = self.remove_token(token_stack, token)
                    if removed:
                        skip = False
                    else:
                        skip = True

            if not skip:
                # Append text preceding matched token
                start_pos = match.start(group)
                if start_pos > last_pos:
                    single_params = params.copy()
                    single_params['text'] = self.postprocess(
                        text[last_pos:start_pos]
                    )
                    yield Segment(**single_params)

                # Actions specific for start token or single token
                if match_type == MatchType.start:
                    token_stack.append(token)
                elif match_type == MatchType.single:
                    single_params = params.copy()
                    single_params['text'] = match.group(group)
                    single_params.update(token.params)
                    yield Segment(token=token, match=match, **single_params)

                # Move last position pointer to the end of matched token
                last_pos = match.end(group)

        # Append anything that's left
        if last_pos < len(text):
            params = self.get_params(token_stack)
            params['text'] = self.postprocess(text[last_pos:])
            yield Segment(**params)
