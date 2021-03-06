#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import unittest

from fetcher.driverutils import (format_date,
                                 driver_cookie_jar_to_requests_cookies,
                                 set_value_js)


class DriverUtilsTestCase(unittest.TestCase):
    def test_formats_date(self):
        self.assertEqual(format_date(datetime.date(2020, 1, 6)),
                         "2020-01-06T00:00:00.000Z")

    def test_set_value_js_gives_correct_js(self):
        self.assertEqual(set_value_js('yolo'), 'arguments[0].value = "yolo"')

    def test_transforms_cookie_jars(self):
        self.assertEqual(
            driver_cookie_jar_to_requests_cookies([{
                'name': 'HOST',
                'value': 'example.com'
            }]), {'HOST': 'example.com'})
