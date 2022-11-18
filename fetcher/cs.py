"""Charles Schwab browser automation tools."""
import pathlib
from typing import NamedTuple

import playwright
import playwright.sync_api

from fetcher.playwrightutils import new_file_preserver


class Credentials(NamedTuple):
    id: str
    pwd: str


def trigger_transaction_history_export(page: playwright.sync_api.Page):
    page.goto('https://client.schwab.com/app/accounts/transactionhistory/#/')
    with page.expect_popup() as popup_info:
        page.locator("#bttnExport button").click()
    popup = popup_info.value
    try:
        popup.locator(
            '#ctl00_WebPartManager1_wpExportDisclaimer_ExportDisclaimer_btnOk'
        ).click()
    except playwright._impl._api_types.Error as e:  # type: ignore
        if not e.message.startswith("Target closed"):
            raise e
        # Playwright for some reason throws "Target closed" error after the
        # click. It doesn't interfere with the download so, just ignore it.


def login(page: playwright.sync_api.Page, creds: Credentials) -> None:
    """Logs in to Charles Schwab.

    Returns once the authentication process finishes. The page will contain
    Charles Schwab's dashboard.

    :param page playwright.sync_api.Page: A blank page.
    :param creds Credentials
    :rtype None
    """
    page.goto(
        'https://client.schwab.com/Login/SignOn/CustomerCenterLogin.aspx')
    page.locator("#loginIdInput:focus")
    page.locator("#passwordInput")
    page.keyboard.type(creds.id)
    page.keyboard.press('Tab')
    page.keyboard.type(creds.pwd)
    page.keyboard.press('Enter')
    page.locator('#placeholderCode').focus()
    page.wait_for_url('https://client.schwab.com/clientapps/**')


def download_transaction_history(page: playwright.sync_api.Page,
                                 creds: Credentials,
                                 download_dir: pathlib.Path) -> None:
    """
    Downloads Charles Schwab's transaction history.

    :param page playwright.sync_api.Page: A blank page.
    :param creds Credentials
    :param download_dir pathlib.Path:
        The download directory used by the browser.
    :rtype None
    """
    login(page, creds)
    with new_file_preserver(download_dir):
        trigger_transaction_history_export(page)
