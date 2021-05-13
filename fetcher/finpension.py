# -*- coding: utf-8 -*-
from typing import NamedTuple
from selenium import webdriver  # type: ignore


class Credentials(NamedTuple):
    id: str
    pwd: str


def fetch_data(creds: Credentials,
               driver: webdriver.remote.webdriver.WebDriver) -> bytes:
    """Fetches Finpensions' transaction data.

    Returns:
        A CSV UTF-8 encoded string with the fetched transactions.
    """
    return b''
