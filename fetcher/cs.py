# -*- coding: utf-8 -*-
"""This modules implements Charles Schwab statement fetchers."""
from typing import NamedTuple
from selenium import webdriver  # type: ignore


class Credentials(NamedTuple):
    id: str
    pwd: str


def fetch_account_history(creds: Credentials) -> bytes:
    """Fetches Charles Schwab's account history using Selenium

    Returns:
        A CSV UTF-8 encoded statement.
    """
    with webdriver.Firefox() as driver:
        driver.implicitly_wait(30)
        raise NotImplementedError()
