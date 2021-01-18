# -*- coding: utf-8 -*-
import unittest

from fetcher import ib


class IbTestCase(unittest.TestCase):
    def test_decode_account_statement_fetch_response_content(self):
        # A censored response from IB.
        response_content = b'''
            {
                "fileContent": "77u/U3RhdGVtZW50LEhlYWRlcixGaWVsZCBOYW1lLEZpZWxkIFZhbHVlClN0YXRlbWVudCxEYXRhLEJyb2tlck5hbWUsSW50ZXJhY3RpdmUgQnJva2Vycw==",
                "contentType": "text/plain",
                "fileName": "U2000000_20201019_20210116.csv",
                "fileFormat": "TEXT",
                "errors": {},
                "expireSeconds": 3300
            }'''
        self.assertEqual(
            ib.decode_account_statement_fetch_response_content(
                response_content),
            (b'\xef\xbb\xbfStatement,Header,Field Name,Field Value\n' +
             b'Statement,Data,BrokerName,Interactive Brokers'))
