# -*- coding: utf-8 -*-
"""Fetches Coop receipts from supercard.ch."""
from collections.abc import Generator
from typing import NamedTuple
from urllib.parse import parse_qs, urlparse

import requests
from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore


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


def partition(xs: list, condition) -> tuple[list, list]:
    """Partitions a list by the first element that evaluates to True.

    >>> partition([1, 2, 3], lambda x: x == 2)
    ([1], [2, 3])

    >>> partition([1, 2, 3], lambda x: x == 4)
    ([1, 2, 3], [])
    """
    idx = None
    for i, x in enumerate(xs):
        if condition(x):
            idx = i
            break

    if idx is None:
        return (xs, [])
    else:
        return (xs[:idx], xs[idx:])


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

    new_urls, old_urls = partition(
        urls, lambda u: extract_barcode(u) == last_barcode)
    if len(old_urls) == 0:
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


def extract_barcode(url: str) -> str | None:
    """Extracts barcode from a receipt_url.

    >>> extract_barcode('https://www.supercard.ch/bin/coop/kbk/kassenzettelpoc?barcode=9900240383725032200038351955&pdfType=receipt')
    '9900240383725032200038351955'

    >>> extract_barcode('gibberish')
    """
    query_dict: dict[str, list] = parse_qs(urlparse(url)[4])
    return query_dict.get('barcode', [None])[0]


def fetch_receipts(
        driver: webdriver.remote.webdriver.WebDriver,  # type: ignore
        creds: Credentials,
        last_barcode: str | None) -> Generator[Receipt, None, None]:
    driver.implicitly_wait(30)
    login(driver, creds)
    raise Exception("Unimplemented.")
