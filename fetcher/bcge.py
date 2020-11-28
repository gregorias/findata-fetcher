"""Fetches account data from BCGE"""
from typing import NamedTuple
import datetime
import json
import logging

from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore
from selenium.webdriver.support import expected_conditions  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
import requests

from .driverutils import format_date, driver_cookie_jar_to_requests_cookies


class Credentials(NamedTuple):
    id: str
    pwd: str


def login(creds: Credentials,
          driver: webdriver.remote.webdriver.WebDriver) -> None:
    LOGIN_PAGE = 'https://www.bcge.ch/authen/login?lang=de'
    driver.get(LOGIN_PAGE)
    wait = WebDriverWait(driver, 30)
    wait.until(
        expected_conditions.presence_of_element_located((By.ID, 'username')))
    driver.find_element(By.ID, "username").send_keys(creds.id + Keys.TAB)
    driver.find_element(By.ID, "password").send_keys(creds.pwd + Keys.RETURN)


def get_account_id(driver: webdriver.remote.webdriver.WebDriver) -> str:
    wait = WebDriverWait(driver, 30)
    wait.until(
        expected_conditions.presence_of_element_located(
            (By.TAG_NAME, 'iframe')))
    driver.switch_to.frame(0)
    try:
        # We want the page to load fully. Otherwise it seems that statement
        # fetching doesn't work. That's why we wait for the export icon to
        # appear, because it appears relatively late in the loading process.
        wait.until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR,
                 'fin-icon-link[label="Exportieren als PDF"]')))
        wait.until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, 'a.ribbon')))
        ribbons = driver.find_elements(By.CSS_SELECTOR, 'a.ribbon')
        elem_with_account_id = ribbons[0]
        params = json.loads(
            elem_with_account_id.get_attribute('fin-ui-sref-params'))
    finally:
        driver.switch_to.parent_frame()
    return params['accountId']


def download_url_request_json_payload(account_id: str,
                                      from_date: datetime.date,
                                      to_date: datetime.date) -> dict:
    return {
        "ids": [account_id],
        "from": format_date(from_date),
        "to": format_date(to_date),
        "format": "CSV"
    }


def fetch_download_url(driver: webdriver.remote.webdriver.WebDriver,
                       account_id: str) -> str:
    fetch_page = ('https://www.bcge.ch/' +
                  'next/api/accounts/{0}/bookings/export'.format(account_id))
    json_payload = download_url_request_json_payload(
        account_id,
        from_date=datetime.date(2018, 1, 1),
        to_date=datetime.date.today())
    cookies = driver_cookie_jar_to_requests_cookies(driver.get_cookies())
    headers = {'X-CSRF-TOKEN': cookies['CSRF-TOKEN']}
    response = requests.post(fetch_page,
                             headers=headers,
                             cookies=cookies,
                             json=json_payload)
    if not response.ok:
        raise Exception("The URL fetch request has failed. " +
                        ('Response reason: {0}, parameters: {1}'
                         ).format(response.reason, (fetch_page, headers,
                                                    cookies, json_payload)))
    return json.loads(response.content)['data']['downloadUrl']


def fetch_account_statement_csv(driver: webdriver.remote.webdriver.WebDriver,
                                download_url: str) -> bytes:
    fetch_page = 'https://www.bcge.ch/next/' + download_url
    cookies = driver_cookie_jar_to_requests_cookies(driver.get_cookies())
    response = requests.get(fetch_page, cookies=cookies)
    if not response.ok:
        raise Exception("The statement fetch request has failed. " +
                        ('Response reason: {0}, parameters: {1}'
                         ).format(response.reason, (fetch_page, cookies)))
    return response.content


def wait_for_logged_in_state(
        driver: webdriver.remote.webdriver.WebDriver) -> None:
    MAIN_PAGE = 'https://www.bcge.ch/portal/netbanking'
    wait = WebDriverWait(driver, 60)
    wait.until(expected_conditions.url_matches(MAIN_PAGE))


def fetch_all_transactions_since_2018(
        driver: webdriver.remote.webdriver.WebDriver) -> bytes:
    account_id = get_account_id(driver)
    download_url = fetch_download_url(driver, account_id)
    account_statement_raw = fetch_account_statement_csv(driver, download_url)
    return account_statement_raw.decode('latin-1').encode('utf-8')


def fetch_bcge_data(creds: Credentials) -> bytes:
    """Fetches BCGE's transaction data using Selenium

    Returns:
        A CSV UTF-8 encoded string with the fetched transactions.
    """
    with webdriver.Firefox() as driver:
        logging.info("Logging in.")
        login(creds, driver)
        logging.info("Waiting for login.")
        wait_for_logged_in_state(driver)
        logging.info("Fetching transaction data.")
        return fetch_all_transactions_since_2018(driver)
