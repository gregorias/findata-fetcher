# -*- coding: utf-8 -*-
import datetime
import unittest

from fetcher import cs


class CsTestCase(unittest.TestCase):
    def test_payload(self):
        self.assertEqual(
            cs.create_fetch_csv_request_params(datetime.date(2021, 2, 28)), {
                'sortSeq': '1',
                'sortVal': '0',
                'tranFilter': '14|9|10|6|7|0|2|11|8|3|15|5|13|4|12|1',
                'timeFrame': '7',
                'filterSymbol': '',
                'fromDate': '01/24/2017',
                'toDate': '02/28/2021',
                'exportError': '',
                'invalidFromDate': '',
                'invalidToDate': '',
                'symbolExportValue': '',
                'includeOptions': 'N',
                'displayTotal': 'true',
            })
