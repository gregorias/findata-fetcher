"""Fetches Coop receipts from supercard.ch."""
import asyncio
import os
import pathlib
from collections.abc import Iterator
from typing import Callable, NamedTuple
from urllib.parse import parse_qs, urlparse

import playwright.async_api
import requests

from .fileutils import atomic_write


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


async def fetch_receipt_urls(page: playwright.async_api.Page,
                             creds: Credentials) -> list[str]:
    """Fetches receipt URLs from supercard.ch.

    Returns:
        A reverse chronological list of receipt URLs.
    """
    await login(page, creds)
    return await get_receipt_urls(page)


def get_chronological_unprocessed_urls(reverse_chronological_urls: list[str],
                                       last_bc: str | None) -> list[str]:
    """Returns a list of chronological URLs that have not been processed yet."""
    chronological_urls = []
    for url in reverse_chronological_urls:
        if last_bc == extract_bc(url):
            break
        chronological_urls.append(url)
    chronological_urls.reverse()
    return chronological_urls


def fetch_receipts(
        chronological_urls: list[str],
        fetch_receipt_cb: Callable[[str], bytes]) -> Iterator[Receipt]:
    """Fetches receipts from the provided list."""
    for url in chronological_urls:
        bc = extract_bc(url)
        yield Receipt(bc=bc, pdf=fetch_receipt_cb(url))


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
