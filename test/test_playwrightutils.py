import unittest

from fetcher.playwrightutils import (playwright_cookie_jar_to_requests_cookies)
import playwright.async_api


class PlaywrightUtilsTestCase(unittest.TestCase):

    def test_transforms_cookie_jars(self):
        self.assertDictEqual(
            playwright_cookie_jar_to_requests_cookies(
                map(playwright.async_api.Cookie, [{
                    'domain': 'client.schwab.com',
                    'expires': 1666438898,
                    'httpOnly': False,
                    'name': 'oda_cp',
                    'path': '/',
                    'sameSite': 'None',
                    'secure': True,
                    'value': 'oda_cp_value'
                }, {
                    'domain': '.schwab.com',
                    'expires': -1,
                    'httpOnly': False,
                    'name': 's_sess',
                    'path': '/',
                    'sameSite': 'None',
                    'secure': False,
                    'value': 's_sess_value'
                }, {
                    'domain': '.schwab.com',
                    'expires': 2098437064,
                    'httpOnly': False,
                    'name': 's_pers',
                    'path': '/',
                    'sameSite': 'None',
                    'secure': False,
                    'value': 's_pers_value'
                }])), {
                    'oda_cp': 'oda_cp_value',
                    's_sess': 's_sess_value',
                    's_pers': 's_pers_value'
                })
