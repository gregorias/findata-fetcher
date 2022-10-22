"""Charles Schwab browser automation tools."""
import datetime
from typing import NamedTuple

import playwright
from playwright.sync_api import sync_playwright
import requests

from .dateutils import yesterday
from .playwrightutils import playwright_cookie_jar_to_requests_cookies


class Credentials(NamedTuple):
    id: str
    pwd: str


def create_fetch_csv_request_params(to_date: datetime.date):
    return {
        'sortSeq': '1',
        'sortVal': '0',
        'tranFilter': '14|9|10|6|7|0|2|11|8|3|15|5|13|4|12|1',
        'timeFrame': '7',
        'filterSymbol': '',
        'fromDate': '01/24/2017',
        'toDate': to_date.strftime('%m/%d/%Y'),
        'exportError': '',
        'invalidFromDate': '',
        'invalidToDate': '',
        'symbolExportValue': '',
        'includeOptions': 'N',
        'displayTotal': 'true',
    }


def fetch_account_history_csv(cookies: dict[str, str]) -> bytes:
    """Fetches account history CSV through a GET request."""
    GET_URL = ('https://client.schwab.com' +
               '/api/History/Brokerage/ExportTransaction')
    params = create_fetch_csv_request_params(yesterday(datetime.date.today()))
    response = requests.get(GET_URL, params=params, cookies=cookies)
    if not response.ok:
        raise Exception("The statement fetch request has failed. " +
                        ('Response reason: {0}, parameters: {1}'
                         ).format(response.reason, (params, cookies)))
    return response.content


def login(page: playwright.sync_api.Page, creds: Credentials) -> None:
    """Logs in to Charles Schwab.

    Returns once the authentication process finishes. The page will contain
    Charles Schwab's dashboard.

    :param page playwright.sync_api.Page: A blank page.
    :param creds Credentials
    :rtype None
    """
    LOGIN_PAGE = 'https://client.schwab.com/Login/SignOn/CustomerCenterLogin.aspx'
    page.goto(LOGIN_PAGE)
    page.locator("#loginIdInput:focus")
    page.locator("#passwordInput")
    page.keyboard.type(creds.id)
    page.keyboard.press('Tab')
    page.keyboard.type(creds.pwd)
    page.keyboard.press('Enter')
    page.wait_for_url('https://client.schwab.com/clientapps/**')


def fetch_account_history(browser: playwright.sync_api.Browser,
                          page: playwright.sync_api.Page,
                          creds: Credentials) -> bytes:
    """
    Fetches Charles Schwab's account history.

    :param browser playwright.sync_api.Browser
    :param page playwright.sync_api.Page: A blank page.
    :param creds Credentials
    :rtype bytes: A CSV UTF-8 encoded statement.
    """
    login(page, creds)
    if len(browser.contexts) != 1:
        raise Exception("Expected exactly one browser context" +
                        " that corresponds to a CS page.")
    bc: playwright.sync_api.BrowserContext = browser.contexts[0]
    return fetch_account_history_csv(
        playwright_cookie_jar_to_requests_cookies(
            bc.cookies(urls=['https://client.schwab.com'])))
