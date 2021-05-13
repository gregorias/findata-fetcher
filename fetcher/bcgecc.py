# -*- coding: utf-8 -*-
# TODO This module is not finished. I haven't prioritized it, because the
# account's status is linked to BCGE and I'm already handling BCGE, i.e. the
# data is "eventually consistent" so to say.
"""Fetches account data from Viseca"""
import time
from typing import NamedTuple
from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
from selenium.webdriver.support import expected_conditions  # type: ignore


class Credentials(NamedTuple):
    id: str
    pwd: str


LOGIN_PAGE = 'https://one.viseca.ch/login/login'


def login(creds: Credentials,
          driver: webdriver.remote.webdriver.WebDriver) -> None:
    username_field_name = 'Benutzername'
    driver.get(LOGIN_PAGE)
    wait = WebDriverWait(driver, 30)
    wait.until(
        expected_conditions.presence_of_element_located(
            (By.ID, username_field_name)))
    driver.find_element(By.ID,
                        username_field_name).send_keys(creds.id + Keys.TAB)
    time.sleep(1)
    pwd_field = driver.find_element(By.ID, "Passwort")
    pwd_field.send_keys(creds.pwd)
    time.sleep(1)
    pwd_field.send_keys(Keys.RETURN)


def wait_for_login(driver: webdriver.remote.webdriver.WebDriver) -> None:
    wait = WebDriverWait(driver, 30)
    wait.until(
        expected_conditions.url_matches('https://one.viseca.ch/de/cockpit'))


def fetch_latest_bill(driver: webdriver.remote.webdriver.WebDriver):
    driver.get('https://one.viseca.ch/de/rechnungen')
    return driver.find_element(By.CSS_SELECTOR,
                               '#statement-list-statement-date0 a')


def fetch_data(creds: Credentials,
               driver: webdriver.remote.webdriver.WebDriver) -> bytes:
    """Fetches Viseca's transaction data using Selenium

    Returns:
        A CSV UTF-8 encoded string with the fetched transactions.
    """
    login(creds, driver)
    wait_for_login(driver)
    fetch_latest_bill(driver)
    return b''
