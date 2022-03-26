# -*- coding: utf-8 -*-
"""Fetches Coop receipts from supercard.ch."""
from datetime import datetime
from urllib.parse import parse_qs, urlparse
from typing import Generator, NamedTuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


class Credentials(NamedTuple):
    id: str
    pwd: str


def login(driver: webdriver.remote.webdriver.WebDriver,
          creds: Credentials) -> None:
    LOGIN_PAGE = 'https://login.supercard.ch/cas/login?locale=de&service=https://www.supercard.ch/de/app-digitale-services/meine-einkaeufe.html'
    driver.get(LOGIN_PAGE)
    driver.find_element(By.ID, "email").send_keys(creds.id + Keys.TAB)
    driver.find_element(By.ID, "password").send_keys(creds.pwd + Keys.RETURN)


def extract_barcode(url: str) -> str | None:
    """Extracts barcode from a receipt_url.

    >>> extract_barcode('https://www.supercard.ch/bin/coop/kbk/kassenzettelpoc?barcode=9900240383725032200038351955&pdfType=receipt')
    '9900240383725032200038351955'

    >>> extract_barcode('gibberish')
    """
    query_dict: dict[str, list] = parse_qs(urlparse(url)[4])
    return query_dict.get('barcode', [None])[0]


def fetch_receipts(
        driver: webdriver.remote.webdriver.WebDriver, creds: Credentials,
        last_update: datetime) -> Generator[tuple[bytes, str], None, datetime]:
    driver.implicitly_wait(30)
    login(driver, creds)
    raise Exception("Unimplemented.")
    return last_update
