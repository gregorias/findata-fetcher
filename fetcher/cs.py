# -*- coding: utf-8 -*-
"""This module implements Charles Schwab statement fetchers."""
import datetime
import time
from typing import Dict, NamedTuple

from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore
from selenium.webdriver.support import expected_conditions  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
import requests

from .dateutils import yesterday
from .driverutils import driver_cookie_jar_to_requests_cookies


class Credentials(NamedTuple):
    id: str
    pwd: str


def wait_for_pin_number_and_select_it(
        wait: WebDriverWait, driver: webdriver.remote.webdriver.WebDriver):
    wait.until(expected_conditions.url_matches('https://lms.schwab.com/.*'))
    driver.switch_to.window(driver.window_handles[0])
    pin_element = driver.find_element(By.ID, "PinNumber")
    # Initially the element is findable but not clickable. When that happens,
    # the click operation fails, so wait for the element to be visible.
    wait.until(expected_conditions.visibility_of(pin_element))
    pin_element.click()
    return pin_element


def url_is_client_website():
    return expected_conditions.url_matches('https://client.schwab.com/.*')


def wait_for_user_to_provide_pin_and_login(
        driver: webdriver.remote.webdriver.WebDriver) -> None:
    LONG_TIME_IN_SECONDS = 10 * 60
    wait = WebDriverWait(driver, LONG_TIME_IN_SECONDS)
    wait.until(url_is_client_website())


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
    wait_for_pin_number_and_select_it(wait, driver)
    wait_for_user_to_provide_pin_and_login(driver)


def create_fetch_csv_request_params(to_date: datetime.date):
    return {
        'sortSeq': '1',
        'sortVal': '0',
        'tranFilter': '14|9|10|6|7|0|2|11|8|3|15|5|13|4|12|1',
        'timeFrame': '7',
        'filterSymbol': '',
        'fromDate': '01/24/2017',
        'toDate': to_date.strftime('%m/%d/%Y'),
        'exportError': '',
        'invalidFromDate': '',
        'invalidToDate': '',
        'symbolExportValue': '',
        'includeOptions': 'N',
        'displayTotal': 'true',
    }


def fetch_account_history_csv(cookies: Dict[str, str]) -> bytes:
    """Fetches account history CSV through a GET request."""
    GET_URL = ('https://client.schwab.com' +
               '/api/History/Brokerage/ExportTransaction')
    params = create_fetch_csv_request_params(yesterday(datetime.date.today()))
    response = requests.get(GET_URL, params=params, cookies=cookies)
    if not response.ok:
        raise Exception("The statement fetch request has failed. " +
                        ('Response reason: {0}, parameters: {1}'
                         ).format(response.reason, (params, cookies)))
    return response.content


def fetch_account_history(driver: webdriver.remote.webdriver.WebDriver,
                          creds: Credentials) -> bytes:
    """Fetches Charles Schwab's account history using Selenium

    Returns:
        A CSV UTF-8 encoded statement.
    """
    driver.implicitly_wait(30)
    login(creds, driver)
    cookies = driver_cookie_jar_to_requests_cookies(driver.get_cookies())
    return fetch_account_history_csv(cookies)
