# -*- coding: utf-8 -*-
import doctest
from fetcher import coop_supercard


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(coop_supercard))
    return tests
