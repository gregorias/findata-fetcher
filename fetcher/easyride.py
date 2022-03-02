# -*- coding: utf-8 -*-
"""This module EasyRide Quittung from Gmail."""
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
    with gmail.connect(creds) as imap:
        receipt_mail_numbers = gmail.search_for_inbox_mails(
            imap, "EasyRide Kaufquittung")
        for receipt_mail_no in receipt_mail_numbers:
            msg = gmail.fetch_mail(imap, receipt_mail_no)
            pdf_part = list(msg.walk())[4]
            save_file(pdf_part, download_dir)
            gmail.archive_mail(imap, receipt_mail_no)
