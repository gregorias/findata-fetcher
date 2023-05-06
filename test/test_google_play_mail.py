# -*- coding: utf-8 -*-
import unittest

from fetcher.google_play_mail import fetch_and_archive_bills

from .file_extra import load_email, read_file
from .fake_inbox import FakeInbox


class GooglePlayMailTestCase(unittest.TestCase):

    def test_fetches_bills(self):
        google_play_bill_mail = load_email(
            'test/data/google-play-mail-2023-05-04-bytes.email')
        inbox = FakeInbox()
        inbox.add_message_to_inbox(google_play_bill_mail)

        fetched_bills = list(fetch_and_archive_bills(inbox))

        self.assertEqual(len(fetched_bills), 1)
        bill = fetched_bills[0]
        self.assertEqual(bill.subject,
                         'Your Google Play Order Receipt from May 4, 2023')
        self.assertEqual(
            bill.payload,
            read_file('test/data/google-play-mail-2023-05-04-contents.txt',
                      bytes_mode=False,
                      newline=''))
