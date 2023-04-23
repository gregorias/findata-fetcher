# -*- coding: utf-8 -*-
"""This module fetches the Patreon monthly receipt email."""
import contextlib
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
    with contextlib.closing(gmail.connect(creds)) as inbox:
        receipt_mail_numbers = inbox.search_inbox(
            "Your Patreon receipt is here")
        for receipt_mail_number in receipt_mail_numbers:
            msg = inbox.fetch(receipt_mail_number)
            payload = get_text_payload(msg)
            save_file(payload, download_dir)
            inbox.archive(receipt_mail_number)
