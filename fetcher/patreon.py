# -*- coding: utf-8 -*-
"""This module fetches the Patreon monthly receipt email."""
import email.message
from pathlib import PurePath
from imaplib import IMAP4
import time
from typing import List

from . import gmail


def get_text_payload(msg: email.message.Message) -> str:
    try:
        return list(msg.walk())[0].get_payload()[0].get_payload()
    except IndexError as e:
        raise Exception(
            "Couldn't fetch the patreon receipt, " +
            "because Patreon message has an unexpected layout.", e)


def save_file(content, target_dir: PurePath) -> None:
    filename = 'patreon_{timestamp:d}.txt'.format(timestamp=int(time.time() *
                                                                1000))
    with open(target_dir / filename, 'w') as f:
        f.write(content)


def fetch_and_archive_receipts(creds: gmail.Credentials,
                               download_dir: PurePath) -> None:
    with gmail.connect(creds) as imap:
        receipt_mail_numbers = gmail.search_for_inbox_mails(
            imap, "Your Patreon receipt is here")
        for receipt_mail_number in receipt_mail_numbers:
            msg = gmail.fetch_mail(imap, receipt_mail_number)
            payload = get_text_payload(msg)
            save_file(payload, download_dir)
            gmail.archive_mail(imap, receipt_mail_number)
