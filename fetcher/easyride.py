# -*- coding: utf-8 -*-
"""This module EasyRide Quittung from Gmail."""
import contextlib
from email.header import decode_header
from pathlib import PurePath
from imaplib import IMAP4
from typing import List

from . import gmail


def save_file(file_part, target_dir: PurePath) -> None:
    filename, payload = gmail.fetch_file(file_part)
    with open(target_dir / filename, 'wb') as f:
        f.write(payload)


def fetch_and_archive_receipts(creds: gmail.Credentials,
                               download_dir: PurePath) -> None:
    with contextlib.closing(gmail.connect(creds)) as inbox:
        receipt_mail_numbers = inbox.search_inbox("EasyRide Kaufquittung")
        receipt_mail_numbers.extend(inbox.search_inbox("EasyRide Quittung"))
        receipt_mail_numbers.extend(inbox.search_inbox("EasyRide receipt"))
        for receipt_mail_no in receipt_mail_numbers:
            msg = inbox.fetch(receipt_mail_no)
            pdf_part = list(msg.walk())[4]
            save_file(pdf_part, download_dir)
            inbox.archive(receipt_mail_no)
