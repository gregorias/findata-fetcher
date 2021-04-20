# -*- coding: utf-8 -*-
"""This module implements useful gmail functionality."""
import email
from imaplib import IMAP4, IMAP4_SSL
from typing import NamedTuple


class Credentials(NamedTuple):
    id: str
    pwd: str


def connect(creds: Credentials) -> IMAP4_SSL:
    imap = IMAP4_SSL('imap.gmail.com')
    imap.login(creds.id, creds.pwd)
    imap.select()
    return imap


def fetch_mail(imap: IMAP4, num):
    typ, data = imap.fetch(num, '(RFC822)')
    if typ != 'OK':
        raise Exception('Could not fetch the specified mail')
    raw_email = data[0]
    if raw_email is None or isinstance(raw_email, bytes):
        raise Exception('I expected raw_email part to be a tuple.'
                        ' Rewrite your fetching code.')
    msg = email.message_from_bytes(raw_email[1])
    return msg


def archive_mail(imap: IMAP4, num) -> None:
    ret_code, ret_msg = imap.store(num, '+FLAGS', '\\Deleted')
    if ret_code != 'OK':
        raise Exception('Could not archive the email: ' +
                        str((ret_code, ret_msg)))
