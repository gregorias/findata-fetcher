# -*- coding: utf-8 -*-
"""This module fetches Digitec-Galaxus bills."""

import email
from imaplib import IMAP4
from typing import Generator, Tuple
import quopri

from . import gmail
from .emailutils import decoded_header_to_str


def search_for_inbox_mails(imap: IMAP4) -> Generator:
    receipt_mail_numbers = gmail.search_for_inbox_mails(imap, "Bestellung")
    for receipt_mail_number in receipt_mail_numbers:
        msg = gmail.fetch_mail(imap, receipt_mail_number)
        from_field = msg['From']
        if not ('Galaxus' in from_field or 'digitec' in from_field):
            continue
        if 'Danke =?UTF-8?B?ZsO8cg==?= deine Bestellung' in msg['Subject']:
            yield (receipt_mail_number, msg)


def get_payload(msg: email.message.Message) -> str:
    raw_payload = list(msg.walk())[1].get_payload()
    return quopri.decodestring(raw_payload).decode('utf8')


def fetch_and_archive_bills(
        creds: gmail.Credentials) -> Generator[Tuple[str, str], None, None]:
    with gmail.connect(creds) as imap:
        for (msg_no, msg) in search_for_inbox_mails(imap):
            subject = decoded_header_to_str(
                email.header.decode_header(msg['Subject']))
            date_line = msg['Date'] + '\n'
            yield (subject, date_line + get_payload(msg))
            gmail.archive_mail(imap, msg_no)
