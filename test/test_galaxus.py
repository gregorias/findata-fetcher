import email.message
from os import path
import pathlib
import textwrap
import unittest

from . import fake_inbox
from .fake_inbox import FakeInbox
from fetcher.galaxus import fetch_and_archive_bills


def testdata_dir() -> pathlib.Path:
    test_dir = pathlib.Path(path.dirname(path.realpath(__file__)))
    return test_dir / 'data'


def read_file(p: pathlib.Path) -> str:
    with open(p, 'r') as f:
        return f.read()


class GalaxusTestCase(unittest.TestCase):

    def test_fetches_bills(self):
        inbox = FakeInbox()
        # Details from a message I got in 2023-04-12
        galaxus_msg = email.message.Message()
        galaxus_msg.add_header('Delivered-To', 'johndoe@gmail.com')
        galaxus_msg.add_header(
            'Subject', 'Danke =?UTF-8?B?ZsO8cg==?= deine Bestellung 85231628')
        galaxus_msg.add_header('To', 'johndoe@gmail.com')
        galaxus_msg.add_header('Date', 'Wed, 12 Apr 2023 10:40:49 +0000 (UTC)')
        galaxus_msg.add_header('From',
                               'Galaxus <noreply@notifications.galaxus.ch')
        galaxus_msg.add_header('Content-Type', 'text/html; charset=utf-8')
        galaxus_msg.add_header('Content-Transfer-Encoding', 'quoted-printable')
        galaxus_msg.add_header('MIME-Version', '1.0')
        galaxus_msg.set_payload(
            read_file('test/data/galaxus-payload-2023-04-12.txt'))
        inbox.add_message_to_inbox(galaxus_msg)

        fetched_bills = list(fetch_and_archive_bills(inbox))

        self.assertEqual(len(fetched_bills), 1)
        fetched_bill = fetched_bills[0]
        self.assertEqual(fetched_bill.subject,
                         'Danke für deine Bestellung 85231628')
        self.assertEqual(
            fetched_bill.payload,
            textwrap.dedent("""\
            Wed, 12 Apr 2023 10:40:49 +0000 (UTC)
            1×
            Burgerstein
            Omega 3 DHA (100 Stück, Tabletten)
            39.20
            1×
            Burgerstein
            Omega-3 EPA (100 Stück, Kapseln)
            47.20
            1×
            Amazon
            Schutzhülle (Amazon Kindle Paperwhite (2021))
            47.30
            1×
            CO2-Kompensation
            0.36
            Gesamtbetrag
            134.06

            Zahlungsmittel:PayPal
            """))
        for entry in inbox.entries:
            self.assertEqual(entry.state, fake_inbox.ENTRY_STATE.ARCHIVE)
