#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import unittest

from fetcher import bcge


class BcgeTestCase(unittest.TestCase):
    def test_gives_download_payload(self):
        account_id = '789abc'
        from_date = datetime.date(2020, 11, 5)
        to_date = datetime.date(2020, 11, 6)
        expected_payload = {
            'ids': [account_id],
            'from': '2020-11-05T00:00:00.000Z',
            'to': '2020-11-06T00:00:00.000Z',
            'format': 'CSV',
        }
        self.assertEqual(
            bcge.download_url_request_json_payload(account_id, from_date,
                                                   to_date), expected_payload)
