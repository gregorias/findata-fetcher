# -*- coding: utf-8 -*-
"""Fetches Coop receipts from supercard.ch."""
from datetime import datetime
from typing import Generator, NamedTuple


class Credentials(NamedTuple):
    id: str
    pwd: str


def fetch_receipts(
        creds: Credentials,
        last_update: datetime) -> Generator[tuple[bytes, str], None, datetime]:
    raise Exception("Unimplemented.")
    return last_update
