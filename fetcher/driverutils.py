"""A collection of data processing utilities for interaction with websites"""
import datetime

from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore


def format_date(date: datetime.date) -> str:
    """Formats a date into a string download request"""
    return date.strftime("%Y-%m-%dT00:00:00.000Z")


def set_value_js(value: str) -> str:
    return 'arguments[0].value = "{0}"'.format(value)


def set_value(driver: webdriver.remote.webdriver.WebDriver, element,
              value: str) -> None:
    driver.execute_script(set_value_js(value), element)


def get_parent(element):
    return element.find_element(By.XPATH, './..')


def get_next_element_sibling(driver: webdriver.remote.webdriver.WebDriver,
                             elem):
    return driver.execute_script("return arguments[0].nextElementSibling",
                                 elem)


def driver_cookie_jar_to_requests_cookies(driver_cookies: dict) -> dict:
    return {c['name']: c['value'] for c in driver_cookies}


def get_user_agent(driver: webdriver.remote.webdriver.WebDriver) -> str:
    return driver.execute_script("return navigator.userAgent;")
