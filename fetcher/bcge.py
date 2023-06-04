"""Downloads account statement from BCGE using Playwright."""
import asyncio
import logging
from typing import NamedTuple

import playwright
import playwright.async_api

from .playwrightutils import intercept_download

LOGIN_PAGE = 'https://www.bcge.ch/authen/login?lang=de'


class Credentials(NamedTuple):
    id: str
    pwd: str


async def login(page: playwright.async_api.Page, creds: Credentials) -> None:
    """Logs in to Charles Schwab.

    Returns once the authentication process finishes. The page will contain
    BCGE's dashboard.

    :param page playwright.async_api.Page: A blank page.
    :param creds Credentials
    :rtype None
    """
    await page.goto(LOGIN_PAGE)
    await page.get_by_label("Vertragsnummer").click()
    await page.get_by_label("Vertragsnummer").fill(creds.id)
    await page.get_by_label("Vertragsnummer").press("Tab")
    await page.get_by_label("Passwort").fill(creds.pwd)
    await page.get_by_role("button", name="Login").click()
    await page.wait_for_url('https://connect.bcge.ch/#/')


async def trigger_statement_export(page: playwright.async_api.Page) -> None:
    iframe = page.frame_locator("iframe")
    await iframe.get_by_role("button", name="Alle Bewegungen").click()
    await iframe.get_by_role("button", name="Herunterladen").click()
    await iframe.get_by_text("Mit Strichpunkt getrennt (CSV)").click()
    await iframe.get_by_text("Saldo zu jeder Buchung").click()
    await iframe.get_by_text('Von').click()
    await page.keyboard.type("01.04.2023")
    await iframe.get_by_role("button", name="Jetzt herunterladen").click()


async def fetch_account_statement(page: playwright.async_api.Page,
                                  creds: Credentials) -> bytes:
    """
    Fetches BCGE's account statement.

    :param page playwright.async_api.Page: A blank page.
    :param creds Credentials
    :rtype bytes: A CSV UTF-8 encoded string with the fetched
        statement.
    """
    logging.info("Logging in to BCGE.")
    await login(page, creds)
    logging.info("Logged in to BCGE.")
    logging.info("Triggerring statement export.")
    async with intercept_download(page) as download:
        await trigger_statement_export(page)
    logging.info("Finished downloading the account statement.")
    return download.downloaded_content().decode('latin-1').encode('utf-8')
