# -*- coding: utf-8 -*-
import datetime
import unittest

from fetcher import degiro

date = datetime.date


class DegiroTestCase(unittest.TestCase):
    def test_get_account_overview_url(self):
        from_date = date(1991, 1, 1)
        to_date = date(2020, 12, 31)

        self.assertEqual(
            degiro.get_account_overview_url(from_date, to_date),
            ('https://trader.degiro.nl/trader/#/account-overview' +
             '?fromDate=1991-01-01&toDate=2020-12-31&aggregateCashFunds=true' +
             '&currency=All'))
