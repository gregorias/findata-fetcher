# -*- coding: utf-8 -*-
"""This module implements useful Gmail functionality."""
import email
import typing
from email.header import decode_header
from imaplib import IMAP4, IMAP4_SSL
from typing import List, NamedTuple, Tuple


class InboxProtocol(typing.Protocol):
    """A simplified email inbox protocol."""

    def fetch(self, num) -> email.message.Message:
        """Fetches the email with the given number."""
        pass

    def archive(self, num) -> None:
        """Archives the email with the given number."""
        pass

    def search_inbox(self, subject: str) -> list[bytes]:
        """Searches for emails with the given subject in the inbox."""
        pass


class Credentials(NamedTuple):
    id: str
    pwd: str


def fetch_credentials() -> Credentials:
    """Fetches Gmail credentials from my 1Password vault."""
    from . import op
    vault = "Automated Findata"
    item = "Gmail"
    username = op.read(vault, item, "username")
    app_password = op.read(vault, item, "credential")
    return Credentials(id=username, pwd=app_password)


class Gmail:

    def __init__(self, imap: IMAP4):
        self.imap = imap

    def close(self) -> None:
        self.imap.close()
        self.imap.logout()

    def fetch(self, num) -> email.message.Message:
        """Fetches the email with the given number.

        :param num: The email number, e.g., `b'1'`.
        """
        typ, data = self.imap.fetch(num, '(RFC822)')
        if typ != 'OK':
            raise Exception('Could not fetch the specified mail')
        raw_email = data[0]
        if raw_email is None or isinstance(raw_email, bytes):
            raise Exception('I expected raw_email part to be a tuple.'
                            ' Rewrite your fetching code.')
        return email.message_from_bytes(raw_email[1])

    def archive(self, num) -> None:
        """Archives the email with the given number.

        :param num: The email archive, e.g, `b'1'`.
        """
        ret_code, ret_msg = self.imap.store(num, '+FLAGS', '\\Deleted')
        if ret_code != 'OK':
            raise Exception('Could not archive the email: ' +
                            str((ret_code, ret_msg)))

    def search_inbox(self, subject: str) -> list[bytes]:
        """
        Searches for emails with the given subject in the inbox.

        :param subject: The subject to search for.
        :return: A list of found emails, e.g., `[b'1', b'2', b'3']`.
        :raises Exception: Throws an exception if the search failed.
        """
        ret = self.imap.search(None, f'SUBJECT "{subject}"')
        if ret[0] != 'OK':
            raise Exception("Could not search for " + subject + ".")
        return ret[1][0].split()


def connect(creds: Credentials) -> Gmail:
    """Connects to a Gmail account."""
    imap = IMAP4_SSL('imap.gmail.com')
    imap.login(creds.id, creds.pwd)
    imap.select()
    return Gmail(imap)


def get_all_inbox_mails(imap: IMAP4) -> List[bytes]:
    ret = imap.search(None, 'ALL')
    if ret[0] != 'OK':
        raise Exception("Could not get all inbox mails.")
    return ret[1][0].split()


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
