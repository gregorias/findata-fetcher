"""Fetches account statements from Revolut."""
import asyncio
import pathlib
import re
from datetime import date, timedelta
from typing import NamedTuple

import playwright
import playwright.async_api


async def login(page: playwright.async_api.Page) -> None:
    """
    Logs in to Revolut.

    :param page playwright.async_api.Page
    :rtype None
    """
    await page.goto('https://app.revolut.com/start')
    # Assuming that the user uses the QR code login method.
    await page.wait_for_url('https://app.revolut.com/home')


async def accept_cookies_on_revolut(page: playwright.async_api.Page) -> None:
    try:
        async with asyncio.timeout(5):
            await dismiss_cookie_consent_dialog(page)
    except asyncio.TimeoutError:
        # If there's no cookie consent dialog, then just proceed.
        pass


async def dismiss_cookie_consent_dialog(
        page: playwright.async_api.Page) -> None:
    await page.get_by_role("button", name="Allow all cookies").click(timeout=0)


class MonthYear(NamedTuple):
    month: int  # zero-indexed
    year: int


def date_to_month_year(d: date) -> MonthYear:
    """
    >>> date_to_month_year(date(2022, 1, 1))
    MonthYear(month=0, year=2022)
    """
    return MonthYear(month=(d.month - 1), year=d.year)


def three_months_ago(start_date: date) -> date:
    """
    >>> three_months_ago(date(2022, 4, 4))
    datetime.date(2022, 1, 1)
    """
    return start_date - timedelta(93)


def monthYearToRevolutLabel(my: MonthYear) -> str:
    """
    >>> monthYearToRevolutLabel(MonthYear(6, 2022))
    'July 2022'
    """
    months = [
        'January',
        'February',
        'March',
        'April',
        'May',
        'June',
        'July',
        'August',
        'September',
        'October',
        'November',
        'December',
    ]
    return f"{months[my.month]} {my.year}"


async def download_statement(page: playwright.async_api.Page, currency: str,
                             current_year: int, from_my: MonthYear):
    """Downloads a single statement."""
    await page.get_by_role("tab", name="Excel").click()
    await page.get_by_role("button", name=re.compile("account")).click()
    await page.get_by_role("button", name=currency).click()

    # There an input with "Starting on" "May 2025" text.
    # To find it, find the most specific div with that.
    # Searching for just "Starting on" doesn't work, because
    # there's a div for just that, and it doesn't handle clicks.
    await (page.locator("div").filter(
        has_text=re.compile("Starting on")).filter(
            has_text=re.compile(f"{current_year}")).last.click())

    async def get_current_selected_year() -> int | None:
        year_string = await page.locator('div[role="grid"] [role="heading"]'
                                         ).text_content()
        if not year_string:
            return None
        return int(year_string)

    current_selected_year = await get_current_selected_year()

    while current_selected_year and current_selected_year > from_my.year:
        await page.get_by_role("button", name="Previous").click()
        current_selected_year = await get_current_selected_year()

    await page.locator(f'div[aria-label="{monthYearToRevolutLabel(from_my)}"]'
                       ).click()
    async with page.expect_popup():
        await page.locator(
            "//button/span[normalize-space(text()) = 'Generate']").click()
        # There are two options. Either the statement is auto-downloaded
        # or it is being generated and we need to press the download button.
        try:
            await page.get_by_text("Statement is being generated").click(
                timeout=2000)
        except playwright.async_api.TimeoutError:
            # Proceed as if the file will be auto-downloaded.
            return None
        else:
            await page.get_by_role("button", name="Download").click()


async def download_statements(page: playwright.async_api.Page,
                              download_dir: pathlib.Path,
                              currencies: list[str]) -> None:
    """Downloads Revolut's account statements."""
    today = date.today()
    for currency in currencies:
        async with page.expect_download() as download_info:
            await download_statement(page,
                                     currency=currency,
                                     current_year=today.year,
                                     from_my=date_to_month_year(
                                         three_months_ago(today)))
        download = await download_info.value
        await download.save_as(download_dir / download.suggested_filename)


async def login_and_download_statements(page: playwright.async_api.Page,
                                        download_dir: pathlib.Path,
                                        currencies: list[str]) -> None:
    """Logs in and downloads Revolut's account statements."""
    await login(page)
    await accept_cookies_on_revolut(page)
    await page.get_by_role("button", name="Statement").click()
    await download_statements(page, download_dir, currencies)
