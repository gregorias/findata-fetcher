# -*- coding: utf-8 -*-
"""Interactive Brokers interface."""
import base64
import datetime
from decimal import Decimal
from enum import Enum
import json
import logging
from typing import Dict, NamedTuple, Optional

from selenium import webdriver
from seleniumwire import request  # type: ignore
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
import requests

from .dateutils import yesterday
from .driverutils import (driver_cookie_jar_to_requests_cookies, get_parent,
                          set_value)


class Credentials(NamedTuple):
    id: str
    pwd: str


def login(driver: webdriver.remote.webdriver.WebDriver,
          creds: Credentials) -> None:
    LOGIN_PAGE = 'https://www.interactivebrokers.co.uk/sso/Login?RL=1'
    driver.get(LOGIN_PAGE)
    driver.find_element(By.ID, "user_name").send_keys(creds.id + Keys.TAB)
    driver.find_element(By.ID, "password").send_keys(creds.pwd + Keys.RETURN)
    secondFactorSelect = driver.find_element(By.ID, 'sf_select')
    IB_KEY_OPTION_VALUE = '5.2a'
    set_value(driver, secondFactorSelect, IB_KEY_OPTION_VALUE)
    driver.execute_script('arguments[0].onchange()', secondFactorSelect)
    # It's a better design to make this function synchronous and wait for the
    # login to be successful. It is more intuitive. When I use ib.login(...),
    # then I expect that upon return of control. I can use issue further
    # instructions in the logged in state.
    wait_for_logged_in_state(driver)


def wait_for_logged_in_state(
        driver: webdriver.remote.webdriver.WebDriver) -> None:
    wait = WebDriverWait(driver, 120)
    wait.until(
        expected_conditions.presence_of_element_located(
            (By.XPATH, "//*[normalize-space(text()) = 'Your Portfolio']")))


def go_to_reports_page(driver: webdriver.remote.webdriver.WebDriver) -> None:
    driver.get("https://www.interactivebrokers.co.uk" +
               "/AccountManagement/AmAuthentication?action=Statements")
    # Wait for the page to load
    driver.find_elements(
        By.XPATH, "//*[normalize-space(text()) = 'MTM Summary']/../../..")


def format_date(day: datetime.date) -> str:
    return day.strftime("%Y%m%d")


def quarter_ago(day: datetime.date) -> datetime.date:
    return day - datetime.timedelta(days=90)


def decode_account_statement_fetch_response_content(
        response_content: bytes) -> bytes:
    return base64.decodebytes(
        json.loads(response_content)['fileContent'].encode('ascii'))


def get_last_get_request(driver) -> Optional[request.Request]:
    """Returns the last GET request made in this session.

    This GET request can be useful to fetch headers used by the IB app.
    """
    for r in reversed(driver.requests):
        if r.method == 'GET':
            return r
    return None


def fetch_account_statement_csv(
    headers: Dict[str, str],
    cookies: Dict[str, str],
) -> bytes:
    FETCH_URL = ('https://www.interactivebrokers.co.uk' +
                 '/AccountManagement/Statements/Run')
    today = datetime.date.today()
    payload = {
        'format': 13,
        'fromDate': format_date(quarter_ago(today)),
        'reportDate': format_date(yesterday(today)),
        'toDate': format_date(yesterday(today)),
        'language': 'en',
        'period': 'DATE_RANGE',
        'statementCategory': 'DEFAULT_STATEMENT',
        # There's also MTM_SUMMARY but that seems to have a strict subset of
        # what DEFAULT_ACTIVITY has.
        'statementType': 'DEFAULT_ACTIVITY'
    }
    headers = {
        'AM_UUID': headers['am_uuid'],
        'AccountHash': headers['accounthash'],
        'Sec-GPS': '1',
        'SessionId': headers['sessionid'],
        'User-Agent': headers['user-agent'],
    }
    response = requests.get(
        FETCH_URL,
        params=payload,  # type: ignore
        cookies=cookies,
        headers=headers)
    if not response.ok:
        raise Exception("The statement fetch request has failed. " +
                        ('Response reason: {0}, parameters: {1}'
                         ).format(response.reason, (FETCH_URL, cookies)))
    return decode_account_statement_fetch_response_content(response.content)


class DepositSource(Enum):
    """Available deposit sources.

    The value is the IB method name of the source.
    """
    CHARLES_SCHWAB = "Charles Schwab"
    BCGE = "Wire-BCGE"


def set_up_incoming_deposit(driver: webdriver.remote.webdriver.WebDriver,
                            source: DepositSource,
                            value: Decimal) -> dict[str, str]:
    """
    Sets up an incoming deposit on IB.

    :param driver webdriver.remote.webdriver.WebDriver
    :param source DepositSource
    :param value Decimal The deposit value.
    :rtype dict[str, str] Wire instructions.
    """
    driver.get('https://www.interactivebrokers.co.uk' +
               '/AccountManagement/AmAuthentication' +
               '?action=FUND_TRANSFERS&type=DEPOSIT')
    method_selector = driver.find_element(
        By.XPATH, f"//span[normalize-space(text()) = '{source.value}']/../..")
    method_selector_class = method_selector.get_attribute('class')
    assert method_selector_class == 'method-selector', (
        f"Expected to find a method selector element for f{source.name}" +
        f", but found an element of class f{method_selector_class}." +
        f" Something might have changed on the website since implementation.\n"
    )
    method_selector.click()

    amount_input = driver.find_element(By.CSS_SELECTOR, 'input[name="amount"]')
    amount_input.send_keys(str(value) + Keys.TAB)
    submit_button = driver.find_element(
        By.CSS_SELECTOR, '.form-group am-button[btn-type = "primary"]')
    submit_button.click()

    # Verify success
    driver.find_element(
        By.XPATH, "//*[normalize-space(text()) = " +
        "'Provide the following information to your bank to initiate the transfer.'"
        + "]")

    wire_instructions = driver.find_element(By.CSS_SELECTOR,
                                            'wire-destination-bank')
    instructions = {}
    for row in wire_instructions.find_elements(By.CSS_SELECTOR, '.row'):
        labels = row.find_elements(By.CSS_SELECTOR, 'label')
        assert len(labels) == 2, (
            "Expected each wire instructions row to contain two labels" +
            f" but got {len(labels)}. Aborting. " +
            "I have created the deposit intent, so you may need to cancel it.")
        instructions[labels[0].text] = labels[1].text
    return instructions


def fetch_account_statement(
        driver: webdriver.remote.webdriver.WebDriver) -> bytes:
    logging.info("Going to the reports page.")
    go_to_reports_page(driver)
    logging.info("Reports page loaded, fetching cookies.")
    last_get = get_last_get_request(driver)
    if last_get is None:
        raise Exception(
            'Could not fetch the account statement, because we did not ' +
            'find any previous GET requests in the session to initialize ' +
            'the fetch requests ')
    cookies = driver_cookie_jar_to_requests_cookies(driver.get_cookies())
    logging.info("Fetching the CSV file.")
    return fetch_account_statement_csv(dict(last_get.headers), cookies)


def fetch_data(driver: webdriver.remote.webdriver.WebDriver,
               creds: Credentials) -> bytes:
    """Fetches Interactive Brokers's transaction data using Selenium

    Returns:
        A CSV with the fetched transactions.
    """
    driver.implicitly_wait(60)
    login(driver, creds)
    return fetch_account_statement(driver)
