"""Fetches account statements from Degiro."""
import logging
from datetime import date, timedelta
from enum import Enum
from typing import NamedTuple, Optional

import playwright.async_api

from . import op
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


async def fetch_credentials(op_client: op.OpSdkClient) -> Credentials:
    """Fetches Degiro credentials from my 1Password vault."""
    item = "degiro.nl"
    username = await op_client.read(op.FINDATA_VAULT, item, "username")
    password = await op_client.read(op.FINDATA_VAULT, item, "password")
    return Credentials(id=username, pwd=password)


async def fetch_totp(op_client: op.OpSdkClient) -> str:
    """Fetches Degiro TOTP from my 1Password vault."""
    vault_id = await op_client.get_vault_id(op.FINDATA_VAULT)
    item_id = await op_client.get_item_id(vault_id, "degiro.nl")
    try:
        return await op_client.get_totp(vault_id, item_id)
    except Exception as e:
        raise Exception("Failed to fetch the Degiro TOTP.") from e


async def dismiss_cookies_consent_dialog(page: Page,
                                         timeout: Optional[timedelta]) -> None:
    await page.get_by_role("button", name="Allow all cookies").click(
        timeout=timeout / timedelta(milliseconds=1) if timeout else None)


async def login(page: Page, creds: Credentials,
                op_client: op.OpSdkClient) -> None:
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
    await totp_input.fill(await fetch_totp(op_client))
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
