"""A Playwright interface into Finpension."""
import unicodedata
from typing import NamedTuple

import playwright.async_api


class Credentials(NamedTuple):
    phone_number: str
    password: str


async def login(page: playwright.async_api.Page, creds: Credentials) -> None:
    """Logs in to Finpension.

    Returns once the authentication process finishes. Leaves the page on
    Finpension's dashboard.

    :param page playwright.async_api.Page: A blank page.
    :param creds Credentials
    :rtype None
    """
    await page.goto('https://app.finpension.ch/login')
    await page.locator('[name="mobile_number"]').type(creds.phone_number)
    await page.locator('[name="password"]').type(creds.password)
    await page.keyboard.press('Enter')
    await page.wait_for_url('https://app.finpension.ch/dashboard')


async def fetch_current_total(
        logged_in_page: playwright.async_api.Page) -> str:
    """
    Fetches current total from Finpension's dashboard.

    :param logged_in_page playwright.async_api.Page
    :rtype str: A normalized string representing the total account value, e.g.,
                "12'174.52 CHF"

    """
    DASHBOARD_URL = 'https://app.finpension.ch/dashboard'
    if logged_in_page.url != DASHBOARD_URL:
        await logged_in_page.goto(DASHBOARD_URL)
    value = await logged_in_page.locator('.dashboard-product__value'
                                         ).inner_text()
    # Turn "12'174.52\xa0CHF" into 12174.52
    return unicodedata.normalize('NFKC',
                                 value).replace("'", "").removesuffix(" CHF")
