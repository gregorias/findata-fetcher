"""Fetches Coop receipts from supercard.ch."""
from collections.abc import Iterator
from itertools import takewhile
import os
import pathlib
from typing import NamedTuple, AsyncIterator
from urllib.parse import parse_qs, urlparse

import requests
import playwright.async_api

from .fileutils import atomic_write
from . import playwrightutils


class Credentials(NamedTuple):
    id: str
    pwd: str


def fetch_credentials() -> Credentials:
    """Fetches credentials from my 1Password vault."""
    from . import op
    vault = "Automated Findata"
    username = op.read(vault, "supercard.ch", "username")
    password = op.read(vault, "supercard.ch", "password")
    return Credentials(id=username, pwd=password)


async def login(page: playwright.async_api.Page, creds: Credentials) -> None:
    """Logs in to supercard.ch.

    supercard.ch occasionally shows a Recaptcha and requires human
    intervention.
    """
    LOGIN_PAGE = 'https://login.supercard.ch/cas/login?locale=de&service=https://www.supercard.ch/de/app-digitale-services/meine-einkaeufe.html'
    # Wait for the login page to load DOM, but not
    # necessarily for all. Sometimes the page lags a lot
    # (>30s) to load all resources that are not necessary
    # for logging in.
    await page.goto(LOGIN_PAGE, wait_until='domcontentloaded')
    # Give some time for the site to load, since we
    # skipped the full load.
    import asyncio
    await asyncio.sleep(5)
    await page.locator('#email').fill(creds.id)
    await page.keyboard.press("Tab")
    await page.locator('#password').fill(creds.pwd)
    await page.keyboard.press("Tab")
    await page.locator("button.loginbtn").click()


class Receipt(NamedTuple):
    bc: str
    pdf: bytes


async def get_receipt_urls(page: playwright.async_api.Page) -> list[str]:
    """Fetches receipts URLs in reverse chronological order.

    An example URL looks like this: "https://www.supercard.ch/bin/coop/kbk/kassenzettelpoc?bc=n015LJj1UXYxwaaaaaaaaaaa_aaaaaaaaaaaaaaaaaaaaaaaaaaaaa&pdfType=receipt"
    """
    # Wait for the receipt buttons to appear.
    await page.locator(".receipt-button").first.inner_html()
    return await page.locator(".receipt-button").evaluate_all(
        "ns => ns.map(n => n.getAttribute('data-receipturl'))")


def fetch_receipt(url, cookies: dict) -> bytes:
    response = requests.get(url, cookies=cookies)
    if not response.ok:
        raise Exception("The statement fetch request has failed. " +
                        f"Response reason: {response.reason}.")
    return response.content


def extract_bc(url: str) -> str:
    """Extracts bc param from a receipt_url.

    >>> extract_bc('https://www.supercard.ch/bin/coop/kbk/kassenzettelpoc?bc=n015LJj1UXc0zPWlRRNFSgho_uYkB7crgrDgEXLxMev3FV0pZgE27g&pdfType=receipt')
    'n015LJj1UXc0zPWlRRNFSgho_uYkB7crgrDgEXLxMev3FV0pZgE27g'
    """
    query_dict: dict[str, list] = parse_qs(urlparse(url)[4])
    bc = query_dict.get('bc', [None])[0]
    if bc is None:
        raise Exception(f"Could not extract a bc from {url}")
    return bc


async def fetch_receipts(page: playwright.async_api.Page,
                         context: playwright.async_api.BrowserContext,
                         creds: Credentials,
                         last_bc: str | None) -> AsyncIterator[Receipt]:
    """Fetches receipts from supercard.ch.

    Returns:
        Receipts newer than last_bc in chronological order.
    """
    await login(page, creds)
    cookies = playwrightutils.playwright_cookie_jar_to_requests_cookies(
        await context.cookies())
    for url in await get_receipt_urls(page):
        print(url)
        bc = extract_bc(url)
        yield Receipt(bc=bc, pdf=fetch_receipt(url, cookies=cookies))


def load_last_bc(path: pathlib.Path) -> str | None:
    if not path.is_file():
        raise Exception(
            f"The provided last BC filepath ({path}) is not present.")
    with open(path, 'r') as f:
        content = f.read()
    if len(content) == 0:
        return None
    return content.strip()


def save_receipt(target_dir: pathlib.Path, last_bc_filepath: pathlib.Path,
                 receipt: Receipt) -> None:
    target_pdf = target_dir / ("Coop " + receipt.bc + ".pdf")
    atomic_write(target_pdf, receipt.pdf)
    try:
        atomic_write(last_bc_filepath, receipt.bc)
    except:
        os.remove(target_pdf)
        raise
