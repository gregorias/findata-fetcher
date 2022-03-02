# -*- coding: utf-8 -*-
"""This module fetches Digitec-Galaxus bills."""

from typing import Generator, Tuple

from . import gmail


def fetch_and_archive_bills(
        creds: gmail.Credentials) -> Generator[Tuple[str, str], None, None]:
    pass
