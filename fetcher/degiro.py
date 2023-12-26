"""Fetches account statements from Degiro."""
from datetime import date, timedelta
from enum import Enum
import logging
from typing import NamedTuple, Optional

import playwright.async_api

from .playwrightutils import intercept_download

Page = playwright.async_api.Page
PlaywrightTimeOutError = playwright.async_api.TimeoutError

logger = logging.getLogger('fetcher.degiro')


class Credentials(NamedTuple):
    id: str
    pwd: str


class StatementType(Enum):
    """Possible statement types."""
    ACCOUNT = "Account"
    PORTFOLIO = "Portfolio"


def fetch_credentials() -> Credentials:
    """Fetches Degiro credentials from my 1Password vault."""
    from . import op
    username = op.read("Private", "degiro.nl", "username")
    password = op.read("Private", "degiro.nl", "password")
    return Credentials(id=username, pwd=password)


def fetch_totp() -> str:
    """Fetches Degiro TOTP from my 1Password vault."""
    from . import op
    return op.fetch_totp("Private", "degiro.nl")


async def dismiss_cookies_consent_dialog(page: Page,
                                         timeout: Optional[timedelta]) -> None:
    await page.get_by_role("button", name="Allow all cookies").click(
        timeout=timeout / timedelta(milliseconds=1) if timeout else None)


async def login(page: Page, creds: Credentials) -> None:
    """Logs in to Degiro."""
    logger.info("Logging in to Degiro.")
    await page.goto("https://trader.degiro.nl/login/chde/#/login")
    try:
        logging.info("Waiting for a cookie consent dialog.")
        await dismiss_cookies_consent_dialog(page,
                                             timeout=timedelta(seconds=2))
    except PlaywrightTimeOutError:
        logging.info("The cookie consent dialog hasn't appeared. Proceeding.")
        # If there's no cookie consent dialog, then just proceed.
        pass
    logger.info("Entering login credentials.")
    await page.locator("#username").fill(creds.id)
    password_input = page.locator("#password")
    await password_input.fill(creds.pwd)
    await password_input.press("Enter")
    logger.info("Entering TOTP.")
    totp_input = page.get_by_placeholder("012345")
    await totp_input.fill(fetch_totp())
    await totp_input.press("Enter")
    await page.wait_for_url("https://trader.degiro.nl/trader/#/markets")


def get_three_months_ago(start_date: date) -> date:
    return start_date - timedelta(93)


def get_account_overview_url(from_date: date, to_date: date) -> str:
    date_format = "%Y-%m-%d"
    return (
        'https://trader.degiro.nl/trader/#/account-overview' +
        '?fromDate={from_date:s}&toDate={to_date:s}&aggregateCashFunds=true' +
        '&currency=All').format(
            from_date=from_date.strftime(date_format),
            to_date=to_date.strftime(date_format),
        )


async def go_to_account_page(page: Page) -> None:
    logging.info("Going to account page.")
    await page.goto(
        get_account_overview_url(
            from_date=get_three_months_ago(date.today()),
            to_date=date.today(),
        ))


async def go_to_portfolio_page(page: Page) -> None:
    logging.info("Going to portfolio page.")
    await page.get_by_role("link", name="Portfolio", exact=True).click()


async def export_csv(page: Page) -> bytes:
    logging.info("Exporting Degiro CSV.")
    async with intercept_download(page) as download:
        await page.get_by_role("button", name="Export").click()
        await page.get_by_role("link", name="CSV").click()
    return download.downloaded_content()


async def fetch_statement(page: Page, statement_type: StatementType) -> bytes:
    """
    Fetches a statement from Degiro.

    :param page: A logged-in page.
    :param statement_type
    :return: A CSV file.
    """
    if statement_type == StatementType.ACCOUNT:
        await go_to_account_page(page)
    elif statement_type == StatementType.PORTFOLIO:
        await go_to_portfolio_page(page)
    else:
        raise Exception("Unknown statement type: {0}.".format(statement_type))
    return await export_csv(page)
