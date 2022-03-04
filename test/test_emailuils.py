# -*- coding: utf-8 -*-
import unittest
import doctest
from fetcher import emailutils


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(emailutils))
    return tests
