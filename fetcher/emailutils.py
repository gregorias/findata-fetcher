# -*- coding: utf-8 -*-

from typing import List, Optional, Tuple

__all__ = ['decoded_header_to_str']


def decoded_header_to_str(header: List[Tuple[bytes, Optional[str]]]) -> str:
    """Stringifies a decoded header from email.header.decode_header.

    >>> decoded_header_to_str([(b'Danke ', None),
    ...                        (b'f\\xc3\\xbcr', 'utf-8'),
    ...                        (b' deine Bestellung', None)])
    'Danke für deine Bestellung'
    """
    strs = [
        t.decode(charset) if charset else t.decode() for t, charset in header
    ]
    return ''.join(strs)
