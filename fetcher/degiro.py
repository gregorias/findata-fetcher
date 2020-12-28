"""Fetches account statement from Degiro"""
from typing import NamedTuple
import logging

from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore
from selenium.webdriver.support import expected_conditions  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore


class Credentials(NamedTuple):
    id: str
    pwd: str


def login(creds: Credentials,
          driver: webdriver.remote.webdriver.WebDriver) -> None:
    LOGIN_PAGE = 'https://trader.degiro.nl/login/chde/#/login'
    driver.get(LOGIN_PAGE)
    wait = WebDriverWait(driver, 30)
    wait.until(
        expected_conditions.presence_of_element_located((By.ID, 'username')))
    driver.find_element(By.ID, "username").send_keys(creds.id + Keys.TAB)
    driver.find_element(By.ID, "password").send_keys(creds.pwd + Keys.RETURN)


def fetch_statement(creds: Credentials) -> bytes:
    """Fetches Degiro's statement using Selenium

    Returns:
        A CSV UTF-8 encoded statement.
    """
    with webdriver.Firefox() as driver:
        logging.info("Logging in.")
        login(creds, driver)
        logging.info("Waiting for login.")
        logging.info("Fetching transaction data.")
        return b''
