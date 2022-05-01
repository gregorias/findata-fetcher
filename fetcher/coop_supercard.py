# -*- coding: utf-8 -*-
"""Fetches Coop receipts from supercard.ch."""
from collections.abc import Iterator
from itertools import takewhile
import os
import pathlib
from typing import NamedTuple
from urllib.parse import parse_qs, urlparse

import requests
from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore

from .driverutils import driver_cookie_jar_to_requests_cookies
from .fileutils import atomic_write


class Credentials(NamedTuple):
    id: str
    pwd: str


class Receipt(NamedTuple):
    bc: str
    pdf: bytes


def login(
        driver: webdriver.remote.webdriver.WebDriver,  # type: ignore
        creds: Credentials) -> None:
    LOGIN_PAGE = 'https://login.supercard.ch/cas/login?locale=de&service=https://www.supercard.ch/de/app-digitale-services/meine-einkaeufe.html'
    driver.get(LOGIN_PAGE)
    driver.find_element(By.ID, "email").send_keys(creds.id + Keys.TAB)
    driver.find_element(By.ID, "password").send_keys(creds.pwd + Keys.RETURN)


def get_receipt_urls(
        driver: webdriver.remote.webdriver.WebDriver,  # type: ignore
        last_bc: str | None) -> list[str]:
    """Fetches receipts URLs in reverse chronological order."""
    wait = WebDriverWait(driver, 10)
    wait.until(
        expected_conditions.presence_of_element_located(
            (By.CLASS_NAME, "receipt-button")))

    def button_to_url(b) -> str:
        url = b.get_attribute('data-receipturl')
        if url is None:
            raise Exception("Expected the receipt button to have an url, " +
                            f"but got {str(b)}")
        return url

    buttons = driver.find_elements(By.CLASS_NAME, "receipt-button")
    urls = [button_to_url(b) for b in buttons]

    if last_bc is None:
        return urls

    new_urls = list(takewhile(lambda u: extract_bc(u) != last_bc, urls))
    if len(new_urls) == len(urls):
        raise Exception("Could not find a receipt with the provided bc." +
                        " Aborting the function, because that is unexpected " +
                        "and something might be going wrong.")
    return new_urls


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


def fetch_receipts(
        driver: webdriver.remote.webdriver.WebDriver,  # type: ignore
        creds: Credentials,
        last_bc: str | None) -> Iterator[Receipt]:
    """Fetches receipts from supercard.ch.

    Returns:
        Receipts newer than last_bc in chronological order.
    """
    driver.implicitly_wait(30)
    login(driver, creds)
    for url in reversed(get_receipt_urls(driver, last_bc)):
        cookies = driver_cookie_jar_to_requests_cookies(driver.get_cookies())
        yield Receipt(bc=extract_bc(url),
                      pdf=fetch_receipt(url, cookies=cookies))


def load_last_bc(path: pathlib.Path) -> str | None:
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


def fetch_and_save_receipts(
        driver: webdriver.remote.webdriver.WebDriver,  # type: ignore
        creds: Credentials,
        last_bc_filepath: pathlib.Path,
        target_dir: pathlib.Path) -> None:
    if not last_bc_filepath.is_file():
        raise Exception(
            f"The provided last_bc_filepath ({last_bc_filepath}) is not "
            "present.")
    last_bc = load_last_bc(last_bc_filepath)
    for receipt in fetch_receipts(driver, creds, last_bc):
        save_receipt(target_dir=target_dir,
                     last_bc_filepath=last_bc_filepath,
                     receipt=receipt)
