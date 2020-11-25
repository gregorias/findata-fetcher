# -*- coding: utf-8 -*-
# TODO
"""Fetches account statement data from Interactive Brokers"""
from typing import NamedTuple
from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
from selenium.webdriver.support import expected_conditions  # type: ignore


class Credentials(NamedTuple):
    id: str
    pwd: str


LOGIN_PAGE = 'https://www.interactivebrokers.co.uk/sso/Login?RL=1'


def login(creds: Credentials,
          driver: webdriver.remote.webdriver.WebDriver) -> None:
    driver.get(LOGIN_PAGE)
    driver.find_element(By.ID, "user_name").send_keys(creds.id + Keys.TAB)
    driver.find_element(By.ID, "password").send_keys(creds.pwd + Keys.RETURN)


def fetch_all_transactions_since_2018(
        driver: webdriver.remote.webdriver.WebDriver) -> bytes:
    driver.find_element(By.CSS_SELECTOR, '[aria-label="Berichte"]').click()
    mtm_overview_box = driver.find_element_by_xpath(
        "//*[normalize-space(text()) = 'MTM-Übersicht']/../../..")
    mtm_overview_box.find_element(By.CSS_SELECTOR, '.fa-arrow-circle-right')
    return b''


def fetch_data(creds: Credentials) -> bytes:
    """Fetches Interactive Brokers's transaction data using Selenium

    Returns:
        A CSV UTF-8 encoded string with the fetched transactions.
    """
    with webdriver.Firefox() as driver:
        driver.implicitly_wait(10)
        login(creds, driver)
        csv = fetch_all_transactions_since_2018(driver)
        return csv
