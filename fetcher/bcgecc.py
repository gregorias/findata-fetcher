"""Fetches the latest account statement from Viseca."""
import logging
import re
from typing import NamedTuple

import playwright.async_api

from fetcher import playwrightutils

from . import op


class Credentials(NamedTuple):
    id: str
    pwd: str


async def fetch_credentials(op_client: op.OpSdkClient) -> Credentials:
    """Fetches credentials from my 1Password vault."""
    item = "Viseca One"
    username = await op_client.read(op.FINDATA_VAULT, item, "username")
    password = await op_client.read(op.FINDATA_VAULT, item, "password")
    return Credentials(id=username, pwd=password)


async def login(page: playwright.async_api.Page, creds: Credentials) -> None:
    LOGIN_PAGE = 'https://one.viseca.ch/login/login'
    logging.info("Logging in to Viseca.")
    await page.goto(LOGIN_PAGE)
    await page.get_by_role("textbox", name="E-mail address").fill(creds.id)
    await page.get_by_role("textbox", name="Password").fill(creds.pwd)
    await page.get_by_role("button", name="Login").click()
    await page.wait_for_url('https://one.viseca.ch/de/cockpit')
    logging.info("Logged in to Viseca.")


async def go_to_rechnungen(page: playwright.async_api.Page) -> None:
    """Goes to the Rechnungen page.

    Assumes we are already logged in and in the cockpit.
    """
    await page.get_by_role("link", name="Rechnungen", exact=True).click()
    await page.wait_for_url('https://one.viseca.ch/de/rechnungen')
    # Wait till bill items are visible.
    await page.locator('div.transactions-statistic').wait_for()


async def get_bill_table_items(
        page: playwright.async_api.Page) -> list[playwright.async_api.Locator]:
    """Gets all bill table items.

    Assumes we are on the Rechnungen tab.
    """
    return await (page.locator('div.statistic-table').filter(
        has_text=re.compile('.*Rechnung.*')).filter(
            has_text=re.compile('.*1107.*')).all())


async def download_bill(
        page: playwright.async_api.Page,
        bill_table_item: playwright.async_api.Locator) -> bytes:
    title = await bill_table_item.locator('.table-header').inner_text()
    print(f'Downloading a bill for {title}.')
    async with playwrightutils.intercept_download(page) as download:
        async with page.expect_popup() as popup_info:
            await bill_table_item.locator('.table-body').locator('a').filter(
                has_text=re.compile(".*Rechnung.*")).click()
        popup = await popup_info.value
    await popup.close()
    return download.downloaded_content()


async def find_and_download_latest_statement(
        page: playwright.async_api.Page) -> bytes:
    await go_to_rechnungen(page)
    bill_table_items = await get_bill_table_items(page)
    if not bill_table_items:
        raise Exception("No bill items found on the Rechnungen tab.")
    latest_bill_table_item = bill_table_items[0]
    return await download_bill(page, latest_bill_table_item)


async def login_and_download_latest_statement(page: playwright.async_api.Page,
                                              creds: Credentials) -> bytes:
    """Fetches Viseca's transaction data using Playwright.

    Returns:
        PDF bytes representing the latest statement.
    """
    await login(page, creds)
    return await find_and_download_latest_statement(page)
