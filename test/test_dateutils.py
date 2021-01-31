# -*- coding: utf-8 -*-
import datetime
import unittest

from fetcher import dateutils


class DateUtilsTestCase(unittest.TestCase):
    def test_yesterday_gives_correct_date(self):
        self.assertEqual(dateutils.yesterday(datetime.date(2020, 1, 31)),
                         datetime.date(2020, 1, 30))
