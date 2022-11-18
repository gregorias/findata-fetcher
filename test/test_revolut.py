import doctest
from fetcher import revolut


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(revolut))
    return tests
