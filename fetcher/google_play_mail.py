# -*- coding: utf-8 -*-
"""This module fetches Google Play bills that end up in my inbox."""
import dataclasses
import email.message
from typing import Generator

from . import gmail


def search_for_inbox_mails(
    inbox: gmail.InboxProtocol
) -> Generator[tuple[bytes, email.message.Message], None, None]:
    """Searches for Google Play Order receipts."""
    receipt_mail_numbers = inbox.search_inbox("Your Google Play Order Receipt")
    for receipt_mail_number in receipt_mail_numbers:
        msg = inbox.fetch(receipt_mail_number)
        yield (receipt_mail_number, msg)


def extract_bill_text(msg: email.message.Message) -> str:
    """Extracts the bill text from the message."""
    return list(msg.walk())[1].get_payload(decode=True).decode('utf-8')


@dataclasses.dataclass
class GooglePlayBill:
    subject: str
    payload: str


def fetch_and_archive_bills(
        inbox: gmail.InboxProtocol) -> Generator[GooglePlayBill, None, None]:
    """Fetches and archives bills from the given inbox.

    :param inbox
    :return A generator of galaxus bills.
    """
    for (msg_no, msg) in search_for_inbox_mails(inbox):
        yield GooglePlayBill(msg['Subject'], extract_bill_text(msg))
        inbox.archive(msg_no)
