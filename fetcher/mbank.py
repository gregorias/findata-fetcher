"""Fetches transaction history from mBank."""
from typing import NamedTuple

import playwright.async_api

from fetcher import playwrightutils

from . import op


class Credentials(NamedTuple):
    id: str
    pwd: str


async def fetch_credentials(op_client: op.OpSdkClient) -> Credentials:
    """Fetches credentials from my 1Password vault."""
    item = "mbank.pl"
    username = await op_client.read(op.FINDATA_VAULT, item, "username")
    password = await op_client.read(op.FINDATA_VAULT, item, "password")
    return Credentials(id=username, pwd=password)


MBANK_LOGIN_PAGE = 'https://online.mbank.pl/pl/Login/history'
HISTORY_PAGE = 'https://online.mbank.pl/history'


async def login(page: playwright.async_api.Page, creds: Credentials) -> None:
    await page.goto(MBANK_LOGIN_PAGE)
    await page.get_by_role("textbox", name="Identyfikator").click()
    await page.get_by_role("textbox", name="Identyfikator").fill(creds.id)
    await page.get_by_role("textbox", name="Identyfikator").press("Tab")
    await page.get_by_role("textbox", name="Hasło").fill(creds.pwd)
    await page.get_by_role("button", name="Zaloguj się").click()
    await page.locator("[data-test-id=\"SCA\\:UnknownDevice\\:OneTimeAccess\"]"
                       ).click()
    # Alternatively: await page.get_by_role("link", name="Cała historia").click()
    await page.wait_for_url(HISTORY_PAGE)


async def fetch_csv_history(page: playwright.async_api.Page) -> bytes:
    """Fetches Mbank's transaction history.

    Assumes we are on the history page.

    Returns:
        A CSV UTF-8 encoded string with the fetched transactions.
    """
    await page.locator("[data-test-id=\"history\\:exportHistoryMenuTrigger\"]"
                       ).click()
    async with playwrightutils.intercept_download(page) as download:
        await page.locator("[data-test-id=\"list\\:2-listItem\"]").click()
    return download.downloaded_content()


def check_decoding(bs: bytes, encoding: str) -> bool:
    try:
        bs.decode(encoding)
        return True
    except UnicodeDecodeError:
        return False


def transform_and_strip_mbanks_csv(raw_csv: bytes) -> bytes:
    if check_decoding(raw_csv, 'utf-8'):
        csv = raw_csv.decode('utf-8')
    else:
        csv = raw_csv.decode('cp1250')
    csv = csv[csv.find('#Data'):]
    csv = csv.replace('\r\n', '\n')
    # Remove two newlines at the end
    csv = csv[:-2]
    return csv.encode('utf-8')


async def login_and_fetch_history(page: playwright.async_api.Page,
                                  creds: Credentials) -> bytes:
    await login(page, creds)
    raw_csv_history = await fetch_csv_history(page)
    return transform_and_strip_mbanks_csv(raw_csv_history)
