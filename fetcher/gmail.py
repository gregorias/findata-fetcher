# -*- coding: utf-8 -*-
"""This module implements useful gmail functionality."""
import email
from email.header import decode_header
from imaplib import IMAP4, IMAP4_SSL
from typing import List, NamedTuple, Optional, Tuple


class Credentials(NamedTuple):
    id: str
    pwd: str


def connect(creds: Credentials) -> IMAP4_SSL:
    imap = IMAP4_SSL('imap.gmail.com')
    imap.login(creds.id, creds.pwd)
    imap.select()
    return imap


def search_for_inbox_mails(imap: IMAP4, subject: str) -> Optional[List[bytes]]:
    ret = imap.search(None, 'SUBJECT "{subject}"'.format(subject=subject))
    if ret[0] != 'OK':
        return None
    return ret[1][0].split()


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


def fetch_file(file_part) -> Tuple[str, bytes]:
    fn_bytes, fn_encoding = decode_header(file_part.get_filename())[0]
    if fn_encoding is None:
        if isinstance(fn_bytes, str):
            filename = fn_bytes
        else:
            filename = fn_bytes.decode()
    else:
        filename = fn_bytes.decode(fn_encoding)
    payload = file_part.get_payload(decode=True)
    return (filename, payload)


def archive_mail(imap: IMAP4, num) -> None:
    ret_code, ret_msg = imap.store(num, '+FLAGS', '\\Deleted')
    if ret_code != 'OK':
        raise Exception('Could not archive the email: ' +
                        str((ret_code, ret_msg)))
