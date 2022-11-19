# -*- coding: utf-8 -*-
"""Fetches account statements from Revolut."""
import asyncio
from datetime import date, timedelta
import pathlib
from typing import NamedTuple

import playwright
import playwright.async_api
import requests

from fetcher.playwrightutils import preserve_new_file


class Credentials(NamedTuple):
    country_code: str
    phone_number: str
    pin: str


async def login(page: playwright.async_api.Page, creds: Credentials) -> None:
    """
    Logs in to Revolut.

    :param page playwright.async_api.Page
    :param creds Credentials
    :rtype None
    """
    await page.goto('https://app.revolut.com/start')
    await page.locator('input[name="phoneNumber"]').focus()
    await page.keyboard.type(creds.phone_number)
    await page.keyboard.press('Tab')
    await page.keyboard.press('Enter')
    await page.locator('input[pattern="[0-9]"]').first.focus()
    await page.keyboard.type(creds.pin)
    await page.wait_for_url('https://app.revolut.com/home')


async def dismiss_cookie_consent_dialog(
        page: playwright.async_api.Page) -> None:
    await page.locator(
        "//button/span[normalize-space(text()) = 'Allow all cookies']"
    ).click()


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


async def download_statement(page: playwright.async_api.Page, account_no: str,
                             from_my: MonthYear):
    """
    Downloads a single statement.

    :param page playwright.async_api.Page
    :param account_no str
    :param from_my MonthYear
    """
    await page.goto(f'https://app.revolut.com/accounts/{account_no}/statement')
    await page.locator("//button[normalize-space(text()) = 'Excel']").click()
    await page.locator("//div[normalize-space(text()) = 'Starting on']/.."
                       ).click()
    await page.locator(f'div[aria-label="{monthYearToRevolutLabel(from_my)}"]'
                       ).click()
    await page.locator("//button/span[normalize-space(text()) = 'Generate']"
                       ).click()
    # TODO: Handle a case where the file may be already generated and
    # downloaded.
    await page.locator("//button[normalize-space(text()) = 'Download']"
                       ).click()


async def download_statements(page: playwright.async_api.Page,
                              download_dir: pathlib.Path, creds: Credentials,
                              account_nos: list[str]) -> None:
    """
    Downloads Revolut's account statements.

    :param page playwright.async_api.Page
    :param download_dir pathlib.Path
    :param creds Credentials
    :param account_nos list[str]
    :rtype None
    """
    await login(page, creds)
    await dismiss_cookie_consent_dialog(page)
    for account_no in account_nos:
        async with asyncio.timeout(20):
            async with preserve_new_file(download_dir):
                await download_statement(page,
                                         account_no,
                                         from_my=date_to_month_year(
                                             three_months_ago(date.today())))
