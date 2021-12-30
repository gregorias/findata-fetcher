# -*- coding: utf-8 -*-
"""Fetches account statements from Revolut"""
from typing import NamedTuple

from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore

from .driverutils import get_next_element_sibling, get_parent, set_value


class Credentials(NamedTuple):
    country_code: str
    phone_number: str
    pin: str


def find_pin_input_fields(driver: webdriver.remote.webdriver.WebDriver):
    return driver.find_elements(By.CSS_SELECTOR, '[inputmode="numeric"]')


def login(creds: Credentials,
          driver: webdriver.remote.webdriver.WebDriver) -> None:
    driver.implicitly_wait(10)
    LOGIN_PAGE = 'https://app.revolut.com/start'
    driver.get(LOGIN_PAGE)
    form = driver.find_element(By.CSS_SELECTOR, 'form')
    country_code_input, phone_number_input = form.find_elements(
        By.CSS_SELECTOR, 'input')
    set_value(driver, country_code_input, creds.country_code)
    phone_number_input.send_keys(creds.phone_number + Keys.RETURN)

    fields = find_pin_input_fields(driver)
    fields[0].send_keys(creds.pin)


def fetch_data(driver: webdriver.remote.webdriver.WebDriver,
               creds: Credentials) -> None:
    """Fetches Revolut's account statement data using Selenium."""
    login(creds, driver)
