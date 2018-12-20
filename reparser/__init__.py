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
GROUP_REGEX = re.compile(r'\?P<(.+?)>')


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
        for key, match_group in self.params.items():
            if isinstance(match_group, MatchGroup):
                self.params[key] = match_group.get_group_value(token, match)


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
        pattern = GROUP_REGEX.sub(r'?P<{}_\1>'.format(self.name), pattern)
        return r'(?P<{}>{})'.format(group, pattern)


class MatchGroup:
    """Name of regex group which should be replaced by its value when token is parsed"""
    def __init__(
        self,
        group: 'str',
        func: 'Optional[Callable]' = None,
    ):
        self.group = group
        self.func = func if callable(func) else None

    def get_group_value(
        self,
        token: 'Token',
        match: 'Match',
    ) -> 'str':
        """Return value of regex match for the specified group"""
        try:
            value = match.group('{}_{}'.format(token.name, self.group))
        except IndexError:
            # downstream error: invalid nested groups
            value = ''
        return value if self.func is None else self.func(value)


class MatchType(enum.Enum):
    """Type of token matched by regex"""
    start = 1
    end = 2
    single = 3


class TokenStack:
    """Storage for tokens during parsing"""
    def __init__(self):
        self.__data = []

    def get_params(self):
        """Get params from stack of tokens"""
        params = {}
        for token in self.__data:
            params.update(token.params)
        return params

    def remove_token(self, token):
        """Remove last occurrence of token from stack"""
        if self.__data[-1] is token:
            self.__data.pop(-1)
            return True

        # downstream error: imbalanced start/end token
        self.__data.reverse()
        try:
            self.__data.remove(token)
        except ValueError:
            return False
        else:
            return True
        finally:
            self.__data.reverse()

    def add_token(self, token):
        """Add a token to the stack"""
        self.__data.append(token)

    def skip_token(
        self,
        token: 'Token',
        match_type: 'MatchType',
    ):
        """logic for skipping tokens inside a skip-section"""
        if not self.__data:
            return False

        if self.__data[-1].skip:
            if self.__data[-1] is token:
                return match_type != MatchType.end
            return True

        return False


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

    def parse(
        self,
        text: 'str',
    ) -> 'Generator[Segment]':
        """Parse text to obtain list of Segments"""
        text = self.preprocess(text)
        token_stack = TokenStack()
        last_pos = 0

        # Iterate through all matched tokens
        for match in self.regex.finditer(text):
            # Find which token has been matched by regex
            token, match_type, group = self.get_matched_token(match)

            # Get params from stack of tokens
            params = token_stack.get_params()

            # Should we skip interpreting tokens?
            if token_stack.skip_token(token, match_type):
                continue

            # Check for end token first
            if match_type == MatchType.end:
                if not token_stack.remove_token(token):
                    # downstream error: matching start token not found
                    continue

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
                token_stack.add_token(token)
            elif match_type == MatchType.single:
                single_params = params.copy()
                single_params['text'] = match.group(group)
                single_params.update(token.params)
                yield Segment(token=token, match=match, **single_params)

            # Move last position pointer to the end of matched token
            last_pos = match.end(group)

        # Append anything that's left
        if last_pos < len(text):
            params = token_stack.get_params()
            params['text'] = self.postprocess(text[last_pos:])
            yield Segment(**params)
