# -*- coding: utf-8 -*-
"""This modules implements Charles Schwab statement fetchers."""
import time
from typing import NamedTuple

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
    """Logs into the Charles Schwab website"""
    LOGIN_PAGE = 'https://www.schwab.com/public/schwab/client_home#'
    driver.get(LOGIN_PAGE)
    driver.switch_to.frame("lms-home")
    login_id = driver.find_element(By.ID, "LoginId")
    wait = WebDriverWait(driver, 30)
    wait.until(expected_conditions.visibility_of(login_id))
    login_id.send_keys(creds.id + Keys.TAB)
    driver.find_element(By.ID, "Password").send_keys(creds.pwd + Keys.RETURN)


def fetch_account_history(creds: Credentials) -> bytes:
    """Fetches Charles Schwab's account history using Selenium

    Returns:
        A CSV UTF-8 encoded statement.
    """
    with webdriver.Firefox() as driver:
        driver.implicitly_wait(30)
        login(creds, driver)
        raise NotImplementedError()
