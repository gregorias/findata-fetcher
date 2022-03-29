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

from .fileutils import atomic_write


class Credentials(NamedTuple):
    id: str
    pwd: str


class Receipt(NamedTuple):
    barcode: str
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
        last_barcode: str | None) -> list[str]:
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

    if last_barcode is None:
        return urls

    new_urls = list(
        takewhile(lambda u: extract_barcode(u) != last_barcode, urls))
    if len(new_urls) == len(urls):
        raise Exception("Could not find a receipt with the provided barcode." +
                        " Aborting the function, because that is unexpected " +
                        "and something might be going wrong.")
    return new_urls


def fetch_receipt(url) -> bytes:
    response = requests.get(url)
    if not response.ok:
        raise Exception("The statement fetch request has failed. " +
                        f"Response reason: {response.reason}.")
    return response.content


def extract_barcode(url: str) -> str:
    """Extracts barcode from a receipt_url.

    >>> extract_barcode('https://www.supercard.ch/bin/coop/kbk/kassenzettelpoc?barcode=9900240383725032200038351955&pdfType=receipt')
    '9900240383725032200038351955'
    """
    query_dict: dict[str, list] = parse_qs(urlparse(url)[4])
    barcode = query_dict.get('barcode', [None])[0]
    if barcode is None:
        raise Exception(f"Could not extract a barcode from {url}")
    return barcode


def fetch_receipts(
        driver: webdriver.remote.webdriver.WebDriver,  # type: ignore
        creds: Credentials,
        last_barcode: str | None) -> Iterator[Receipt]:
    """Fetches receipts from supercard.ch.

    Returns:
        Receipts newer than last_barcode in chronological order.
    """
    driver.implicitly_wait(30)
    login(driver, creds)
    for url in reversed(get_receipt_urls(driver, last_barcode)):
        yield Receipt(barcode=extract_barcode(url), pdf=fetch_receipt(url))


def load_last_barcode(path: pathlib.Path) -> str | None:
    with open(path, 'r') as f:
        content = f.read()
    if len(content) == 0:
        return None
    return content.strip()


def save_receipt(target_dir: pathlib.Path, last_barcode_filepath: pathlib.Path,
                 receipt: Receipt) -> None:
    target_pdf = target_dir / ("Coop " + receipt.barcode + ".pdf")
    atomic_write(target_pdf, receipt.pdf)
    try:
        atomic_write(last_barcode_filepath, receipt.barcode)
    except:
        os.remove(target_pdf)
        raise


def fetch_and_save_receipts(
        driver: webdriver.remote.webdriver.WebDriver,  # type: ignore
        creds: Credentials,
        last_barcode_filepath: pathlib.Path,
        target_dir: pathlib.Path) -> None:
    if not last_barcode_filepath.is_file():
        raise Exception(
            f"The provided last_barcode_filepath ({last_barcode_filepath})"
            " is not present.")
    last_barcode = load_last_barcode(last_barcode_filepath)
    for receipt in fetch_receipts(driver, creds, last_barcode):
        save_receipt(target_dir=target_dir,
                     last_barcode_filepath=last_barcode_filepath,
                     receipt=receipt)
