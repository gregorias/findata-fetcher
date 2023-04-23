# -*- coding: utf-8 -*-
"""This module fetches Digitec-Galaxus bills."""

import bs4
import contextlib
import dataclasses
import email
from imaplib import IMAP4
from typing import Generator, Tuple
import quopri
import unicodedata

from . import gmail
from .emailutils import decoded_header_to_str


def search_for_inbox_mails(inbox: gmail.InboxProtocol) -> Generator:
    receipt_mail_numbers = inbox.search_inbox("Bestellung")
    for receipt_mail_number in receipt_mail_numbers:
        msg = inbox.fetch(receipt_mail_number)
        from_field = msg['From']
        if not ('Galaxus' in from_field or 'digitec' in from_field):
            continue
        if 'Danke =?UTF-8?B?ZsO8cg==?= deine Bestellung' in msg['Subject']:
            yield (receipt_mail_number, msg)


def get_payload(msg: email.message.Message) -> str:
    payload_bytes = quopri.decodestring(msg.get_payload())
    payload_string = payload_bytes.decode('utf-8').replace('\xa0', ' ')
    soup = bs4.BeautifulSoup(payload_string, 'html.parser')
    tables_with_total = [
        t for t in soup.find_all('table') if 'Gesamtbetrag' in t.text
    ]
    total_row = tables_with_total[-1]
    current = total_row
    # Find the td-element that contains all bill rows. It's the first element
    # that has multiple tables as children.
    while current is not None:
        if len(current.find_all('table', recursive=False)) > 1:
            bill_entries_element = current
            break
        current = current.parent
    if not bill_entries_element:
        raise Exception('Could not find bill entries element')

    return '\n'.join([
        l
        for l in bill_entries_element.get_text('\n', strip=True).splitlines()
        if l != '-'
    ])


@dataclasses.dataclass
class GalaxusBill:
    subject: str
    payload: str


def fetch_and_archive_bills(
        inbox: gmail.InboxProtocol) -> Generator[GalaxusBill, None, None]:
    """Fetches and archives bills from the given inbox.

    :param inbox
    :return A generator of galaxus bills.
    """
    for (msg_no, msg) in search_for_inbox_mails(inbox):
        subject = decoded_header_to_str(
            email.header.decode_header(msg['Subject']))
        date_line = msg['Date'] + '\n'
        yield GalaxusBill(subject=subject,
                          payload=date_line + get_payload(msg))
        inbox.archive(msg_no)
