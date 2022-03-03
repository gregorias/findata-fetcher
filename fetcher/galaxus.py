# -*- coding: utf-8 -*-
"""This module fetches Digitec-Galaxus bills."""

import email
from imaplib import IMAP4
from typing import Generator, Tuple
import quopri

from . import gmail


def search_for_inbox_mails(imap: IMAP4) -> Generator:
    receipt_mail_numbers = gmail.search_for_inbox_mails(imap, "Bestellung")
    for receipt_mail_number in receipt_mail_numbers:
        msg = gmail.fetch_mail(imap, receipt_mail_number)
        from_field = msg['From']
        if not ('Galaxus' in from_field or 'Digitec' in from_field):
            continue
        if 'Danke =?UTF-8?B?ZsO8cg==?= deine Bestellung' in msg['Subject']:
            yield (receipt_mail_number, msg)


def get_payload(msg: email.message.Message) -> str:
    raw_payload = list(msg.walk())[1].get_payload()
    return quopri.decodestring(raw_payload).decode('utf8')


def fetch_and_archive_bills(
        creds: gmail.Credentials) -> Generator[str, None, None]:
    with gmail.connect(creds) as imap:
        for (msg_no, msg) in search_for_inbox_mails(imap):
            yield get_payload(msg)
