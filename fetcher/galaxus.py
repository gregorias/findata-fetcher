# -*- coding: utf-8 -*-
"""This module fetches Digitec-Galaxus bills."""

from imaplib import IMAP4
from typing import Generator, Tuple

from . import gmail


def search_for_inbox_mails(imap: IMAP4, subject: str) -> Generator:
    receipt_mail_numbers = gmail.search_for_inbox_mails(imap, subject)
    for receipt_mail_number in receipt_mail_numbers:
        yield gmail.fetch_mail(imap, receipt_mail_number)


def fetch_and_archive_bills(creds: gmail.Credentials) -> Generator:
    with gmail.connect(creds) as imap:
        for msg in search_for_inbox_mails(imap, "Bestellung"):
            yield msg
