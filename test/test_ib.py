# -*- coding: utf-8 -*-
import csv
import unittest
import os.path as path
import pathlib

from fetcher import ib


def testdata_dir() -> pathlib.Path:
    test_dir = pathlib.Path(path.dirname(path.realpath(__file__)))
    return test_dir / 'data'


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

    def test_wire_instructions(self):

        def read_csv(p: pathlib.Path) -> dict[str, str]:
            result = dict()
            with open(p, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    result[row['key']] = row['value']
            return result

        self.assertEqual(
            ib.wire_instructions(
                read_csv(testdata_dir() / 'ib-wire-instructions.csv')),
            ib.WireInstructions(to_beneficiary_title="""Interactive Brokers LLC
One Pickwick Plaza
Greenwich, Connecticut 06830
United States""",
                                bank_account_number="633736902",
                                aba_routing_number="021000021",
                                swift_bic_code="CHASUS33XXX",
                                beneficiary_bank="""JPMORGAN CHASE BANK, N.A.
383 Madison Avenue
New York 10017
United States"""))

    def test_wire_instructions_throws_exception_on_empty_dict(self):
        with self.assertRaises(Exception):
            ib.wire_instructions(dict())
