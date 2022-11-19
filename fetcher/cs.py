"""Charles Schwab browser automation tools."""
import asyncio
import pathlib
from typing import NamedTuple

import playwright
import playwright.async_api

from fetcher.playwrightutils import preserve_new_file


class Credentials(NamedTuple):
    id: str
    pwd: str


async def trigger_transaction_history_export(page: playwright.async_api.Page):
    await page.goto(
        'https://client.schwab.com/app/accounts/transactionhistory/#/')
    async with page.expect_popup() as popup_info:
        await page.locator("#bttnExport button").click()
    popup = await popup_info.value
    try:
        await popup.locator(
            '#ctl00_WebPartManager1_wpExportDisclaimer_ExportDisclaimer_btnOk'
        ).click()
    except playwright._impl._api_types.Error as e:  # type: ignore
        if not e.message.startswith("Target closed"):
            raise e
        # Playwright for some reason throws "Target closed" error after the
        # click. It doesn't interfere with the download so, just ignore it.


async def login(page: playwright.async_api.Page, creds: Credentials) -> None:
    """Logs in to Charles Schwab.

    Returns once the authentication process finishes. The page will contain
    Charles Schwab's dashboard.

    :param page playwright.async_api.Page: A blank page.
    :param creds Credentials
    :rtype None
    """
    await page.goto(
        'https://client.schwab.com/Login/SignOn/CustomerCenterLogin.aspx')
    await page.frame_locator('#lmsSecondaryLogin').get_by_placeholder(
        'Login ID').focus()
    await page.keyboard.type(creds.id)
    await page.keyboard.press('Tab')
    await page.keyboard.type(creds.pwd)
    await page.keyboard.press('Enter')
    await page.locator('#placeholderCode').focus()
    await page.wait_for_url('https://client.schwab.com/clientapps/**')


async def download_transaction_history(page: playwright.async_api.Page,
                                       creds: Credentials,
                                       download_dir: pathlib.Path) -> None:
    """
    Downloads Charles Schwab's transaction history.

    :param page playwright.async_api.Page: A blank page.
    :param creds Credentials
    :param download_dir pathlib.Path:
        The download directory used by the browser.
    :rtype None
    """
    await login(page, creds)
    async with asyncio.timeout(20):  # type: ignore
        async with preserve_new_file(download_dir):
            await trigger_transaction_history_export(page)
