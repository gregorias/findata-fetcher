#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest

from fetcher import tool
from fetcher import mbank


class ToolTestCase(unittest.TestCase):
    def test_extract_mbank_credentials(self):
        config = {'mbank_id': '123', 'mbank_pwd': 'hunter2'}
        expected_credentials = mbank.Credentials(id='123', pwd='hunter2')

        self.assertEqual(expected_credentials,
                         tool.extract_mbank_credentials(config))
