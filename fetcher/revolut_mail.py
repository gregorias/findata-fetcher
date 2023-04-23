# -*- coding: utf-8 -*-
"""This module fetches the Revolut statements shared on Gmail."""
import contextlib
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
                r'^account-statement_\d*-\d*-\d*_\d*-\d*-\d*_de-ch_[0-9a-f]*.csv$',
                filename):
            return part
    return None


def get_revolut_mail_numbers(inbox: gmail.Gmail) -> List[bytes]:
    """Returns mail numbers containing a Revolut statement."""
    all_emails = gmail.get_all_inbox_mails(inbox.imap)
    if all_emails is None:
        raise Exception("Could not fetch the email list from gMail.")
    revolut_emails = []
    for email_no in all_emails:
        msg = inbox.fetch(email_no)
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
    with contextlib.closing(gmail.connect(creds)) as inbox:
        revolut_mail_numbers = get_revolut_mail_numbers(inbox)
        for revolut_mail_no in revolut_mail_numbers:
            msg = inbox.fetch(revolut_mail_no)
            csv_part = get_revolut_statement_part(msg)
            save_file(csv_part, download_dir)
            inbox.archive(revolut_mail_no)
