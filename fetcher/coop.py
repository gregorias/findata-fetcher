# -*- coding: utf-8 -*-
"""This module fetching the Coop receipt from gmail."""
from email.header import decode_header
from pathlib import PurePath
from imaplib import IMAP4
from typing import List

from . import gmail

# > imap.search(None, 'SUBJECT "Ihr digitaler Kassenzettel"')
# ('OK', [b'1 2'])


def get_receipt_mail_numbers(imap: IMAP4) -> List[bytes]:
    ret = imap.search(None, 'SUBJECT "Ihr digitaler Kassenzettel"')
    if ret[0] != 'OK':
        raise Exception("Could not search for Coop receipts.")
    return ret[1][0].split()


def save_file(file_part, target_dir: PurePath) -> None:
    fn_bytes, fn_encoding = decode_header(file_part.get_filename())[0]
    if fn_encoding is None:
        raise Exception("Filename encoding for " + str(fn_bytes) +
                        " was None.")
    filename = fn_bytes.decode(fn_encoding)
    with open(target_dir / filename, 'wb') as f:
        f.write(file_part.get_payload(decode=True))


def fetch_and_archive_receipts(creds: gmail.Credentials,
                               download_dir: PurePath) -> None:
    with gmail.connect(creds) as imap:
        receipt_mail_numbers = get_receipt_mail_numbers(imap)
        for receipt_mail_no in receipt_mail_numbers:
            msg = gmail.fetch_mail(imap, receipt_mail_no)
            pdf_part = list(msg.walk())[2]
            save_file(pdf_part, download_dir)
            gmail.archive_mail(imap, receipt_mail_no)
