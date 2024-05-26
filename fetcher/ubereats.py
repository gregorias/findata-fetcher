"""This module fetches the Uber Eats bill email."""
import contextlib
import email.message
import quopri
from typing import Generator, Tuple

from bs4 import BeautifulSoup

from . import gmail


def get_html_payload(msg: email.message.Message) -> str:
    try:
        return str(list(msg.walk())[0].get_payload())
    except IndexError as e:
        raise Exception(
            "Couldn't fetch the Uber Eats bill, " +
            "because the message has an unexpected layout.", e)


def get_payments_string(soup) -> str:
    payments_node = soup.find(lambda e: e.text == 'Payments')
    return payments_node.parent.parent.parent.parent.text


def fetch_and_archive_bills(
        creds: gmail.Credentials) -> Generator[Tuple[str, str], None, None]:
    with contextlib.closing(gmail.connect(creds)) as inbox:
        receipt_mail_numbers = inbox.search_inbox("order with Uber Eats")
        for receipt_mail_number in receipt_mail_numbers:
            msg = inbox.fetch(receipt_mail_number)
            html_page = quopri.decodestring(
                get_html_payload(msg).encode('ascii'))
            soup = BeautifulSoup(html_page, features='html.parser')
            yield (msg['Date'], get_payments_string(soup))
            inbox.archive(receipt_mail_number)
