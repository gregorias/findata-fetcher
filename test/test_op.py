import os
import unittest

from fetcher import op


class OpTestCase(unittest.TestCase):

    def test_set_service_account_auth_token_sets_and_restores(self):
        os.environ['OP_SERVICE_ACCOUNT_TOKEN'] = 'bar'
        with op.set_service_account_auth_token('foo'):
            self.assertEqual(os.environ['OP_SERVICE_ACCOUNT_TOKEN'], 'foo')
        self.assertEqual(os.environ['OP_SERVICE_ACCOUNT_TOKEN'], 'bar')

    def test_set_service_account_auth_token_sets_and_clears(self):
        if os.environ.get('OP_SERVICE_ACCOUNT_TOKEN') is not None:
            del os.environ['OP_SERVICE_ACCOUNT_TOKEN']
        with op.set_service_account_auth_token('foo'):
            self.assertEqual(os.environ['OP_SERVICE_ACCOUNT_TOKEN'], 'foo')
        self.assertEqual(os.environ.get('OP_SERVICE_ACCOUNT_TOKEN'), None)
