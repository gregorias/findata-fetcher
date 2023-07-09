# -*- coding: utf-8 -*-
"""Interactive Brokers interface."""
import base64
import datetime
import dataclasses
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


class WireInstructions(NamedTuple):
    to_beneficiary_title: str
    bank_account_number: str
    aba_routing_number: str
    swift_bic_code: str
    beneficiary_bank: str


def wire_instructions(csv: dict[str, str]) -> WireInstructions:
    """
    Constructs WireInstructions from the dict returned by `set_up_deposit`.

    :param csv dict[str, str]
    :rtype WireInstructions
    """
    to_beneficiary_title = csv.get("Wire Funds to Beneficiary/Account Title")
    bank_account_number = csv.get("Bank Account Number")
    aba_routing_number = csv.get("ABA Routing Number")
    swift_bic_code = csv.get("SWIFT/BIC Code")
    beneficiary_bank = csv.get("Beneficiary Bank")

    if (to_beneficiary_title is None or bank_account_number is None
            or aba_routing_number is None or swift_bic_code is None
            or beneficiary_bank is None):
        raise Exception(
            "Could not find one or more required fields for wire instructions."
        )
    return WireInstructions(to_beneficiary_title=to_beneficiary_title,
                            bank_account_number=bank_account_number,
                            aba_routing_number=aba_routing_number,
                            swift_bic_code=swift_bic_code,
                            beneficiary_bank=beneficiary_bank)


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
