MARKDOWN_TEXT_EXAMPLE = (
    'Hello **bold** world!\nYou can **try *this* awesome** [link](www.eff.org).'
)

MARKDOWN_SERIALIZED_SEGMENTS_EXAMPLE = [
    ('Hello ', {}),
    ('bold', {'is_bold': True}),
    (' world!', {}),
    ('\n', {'segment_type': 'LINE_BREAK'}),
    ('You can ', {}),
    ('try ', {'is_bold': True}),
    ('this', {'is_bold': True, 'is_italic': True}),
    (' awesome', {'is_bold': True}),
    (' ', {}),
    ('link', {'link_target': 'http://www.eff.org'}),
    ('.', {})
]
