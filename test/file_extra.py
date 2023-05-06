# -*- coding: utf-8 -*-
"""Extra utilities related to file I/O."""
import email.message
from email.parser import BytesParser


def read_file(path: str, bytes_mode: bool = False, **kwargs):
    """Reads the contents of a file.

    Returns either string or bytes depending on the value of `bytes_mode`.
    """
    with open(path, 'r' + ('b' if bytes_mode else ''), **kwargs) as f:
        return f.read()


def load_email(path: str) -> email.message.Message:
    """Loads an email from a file."""
    email_bytes: bytes = read_file(path, bytes_mode=True)
    return BytesParser().parsebytes(email_bytes)
