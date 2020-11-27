# -*- coding: utf-8 -*-
# TODO clean up and test up
"""Fetches account statement data from Interactive Brokers"""
import base64
import json
from typing import NamedTuple
from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
from selenium.webdriver.support import expected_conditions  # type: ignore
import requests

from .driverutils import format_date, driver_cookie_jar_to_requests_cookies


class Credentials(NamedTuple):
    id: str
    pwd: str


LOGIN_PAGE = 'https://www.interactivebrokers.co.uk/sso/Login?RL=1'


def login(creds: Credentials,
          driver: webdriver.remote.webdriver.WebDriver) -> None:
    driver.get(LOGIN_PAGE)
    driver.find_element(By.ID, "user_name").send_keys(creds.id + Keys.TAB)
    driver.find_element(By.ID, "password").send_keys(creds.pwd + Keys.RETURN)


def set_value(driver, element, value: str) -> None:
    driver.execute_script('arguments[0].value = "{0}"'.format(value), element)


def use_the_modal_box_to_download_the_csv(
        driver: webdriver.remote.webdriver.WebDriver):
    mtm_summary_modal = driver.find_element(By.CSS_SELECTOR, '#amModalBody')

    period_select = mtm_summary_modal.find_element(By.CSS_SELECTOR, 'select')
    # Wait till the date rage selector is filled
    period_select.find_element(By.CSS_SELECTOR, ':not([value="?"])')
    set_value(driver, period_select, 'string:DATE_RANGE')
    # jQuery is necessary to trigger callbacks that process the form.
    driver.execute_script('$(arguments[0]).trigger("change")', period_select)

    date_range = mtm_summary_modal.find_element(By.CSS_SELECTOR,
                                                'am-date-range-picker')
    # [from, to] = dateRange.querySelectorAll('input');
    # from.value = twoMonthsAgo();
    # $(from).trigger('change');

    format_select = mtm_summary_modal.find_elements(By.CSS_SELECTOR,
                                                    'select')[1]
    set_value(driver, format_select, 'string:13')
    driver.execute_script('$(arguments[0]).trigger("change")', format_select)

    return mtm_summary_modal, date_range


# TODO adjust name
def fetch_all_transactions_since_2018(
        driver: webdriver.remote.webdriver.WebDriver):
    driver.find_element(By.CSS_SELECTOR, '[aria-label="Reports"]').click()
    mtm_summary_box = driver.find_element_by_xpath(
        "//*[normalize-space(text()) = 'MTM Summary']/../../..")
    mtm_summary_box.find_element(By.CSS_SELECTOR,
                                 '.fa-arrow-circle-right').click()
    return use_the_modal_box_to_download_the_csv(driver)


def fetch_account_statement_csv(
        driver: webdriver.remote.webdriver.WebDriver) -> bytes:
    fetch_url = 'https://www.interactivebrokers.co.uk/AccountManagement/Statements/Run'
    payload = {
        'format': 13,
        'fromDate': '20201126',
        'reportDate': '20201126',
        'toDate': '20201126',
        'language': 'en',
        'period': 'DATE_RANGE',
        'statementCategory': 'DEFAULT_STATEMENT',
        'statementType': 'MTM_SUMMARY'
    }
    cookies = driver_cookie_jar_to_requests_cookies(driver.get_cookies())
    am_session_id = driver.execute_script('return AM_SESSION_ID;')
    headers = {
        'SessionId': am_session_id,
    }
    response = requests.get(
        fetch_url,
        params=payload,  # type: ignore
        cookies=cookies,
        headers=headers)
    if not response.ok:
        raise Exception("The statement fetch request has failed. " +
                        ('Response reason: {0}, parameters: {1}'
                         ).format(response.reason, (fetch_url, cookies)))
    return base64.decodebytes(json.loads(response.content)['fileContent'])


# https://www.interactivebrokers.co.uk/AccountManagement/Statements/Run?format=13&fromDate=20200428&language=en&period=DATE_RANGE&reportDate=20201125&statementCategory=DEFAULT_STATEMENT&statementType=MTM_SUMMARY&toDate=20201125
# Gives back a json


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
