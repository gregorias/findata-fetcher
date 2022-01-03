# -*- coding: utf-8 -*-
"""This module fetches the Revolut statements shared on Gmail."""
import email
from email.header import decode_header
from pathlib import PurePath
from imaplib import IMAP4
from typing import List, Optional
import re

from . import gmail


def get_revolut_statement_part(
        msg: email.message.Message) -> Optional[email.message.Message]:
    for part in msg.walk():
        filename = part.get_filename()
        if not filename: continue

        if re.match(
                '^account-statement_\d*-\d*-\d*_\d*-\d*-\d*_de-ch_[0-9a-f]*.csv$',
                filename):
            return part
    return None


def get_revolut_mail_numbers(imap: IMAP4) -> List[bytes]:
    """Returns mail numbers containing a Revolut statement."""
    all_emails = gmail.get_all_inbox_mails(imap)
    if all_emails is None:
        raise Exception("Could not fetch the email list from gMail.")
    revolut_emails = []
    for email_no in all_emails:
        msg = gmail.fetch_mail(imap, email_no)
        if get_revolut_statement_part(msg):
            revolut_emails.append(email_no)
    return revolut_emails


def save_file(file_part, target_dir: PurePath) -> None:
    filename, payload = gmail.fetch_file(file_part)
    filename = 'revolut-' + filename
    with open(target_dir / filename, 'wb') as f:
        f.write(payload)


def fetch_and_archive_statements(creds: gmail.Credentials,
                                 download_dir: PurePath) -> None:
    with gmail.connect(creds) as imap:
        revolut_mail_numbers = get_revolut_mail_numbers(imap)
        for revolut_mail_no in revolut_mail_numbers:
            msg = gmail.fetch_mail(imap, revolut_mail_no)
            csv_part = get_revolut_statement_part(msg)
            save_file(csv_part, download_dir)
            gmail.archive_mail(imap, revolut_mail_no)
