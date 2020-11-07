"""Fetches account data from BCGE"""
from typing import NamedTuple
import datetime
from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
from selenium.webdriver.support import expected_conditions  # type: ignore
import requests


class Credentials(NamedTuple):
    id: str
    pwd: str


def login_to_bcge(creds: Credentials,
                  driver: webdriver.remote.webdriver.WebDriver) -> None:
    pass


def fetch_all_transactions_since_2018(
        driver: webdriver.remote.webdriver.WebDriver) -> bytes:
    return b''


def fetch_bcge_data(creds: Credentials) -> bytes:
    """Fetches BCGE's transaction data using Selenium

    Returns:
        A CSV UTF-8 encoded string with the fetched transactions.
    """
    with webdriver.Firefox() as driver:
        login_to_bcge(creds, driver)
        csv = fetch_all_transactions_since_2018(driver)
        return csv
