# -*- coding: utf-8 -*-
# TODO This module is not finished. I haven't prioritized it, because the
# account's status is linked to BCGE and I'm already handling BCGE, i.e. the
# data is "eventually consistent" so to say.
"""Fetches account data from Viseca"""
import re
import time
from typing import NamedTuple

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from . import op
from .driverutils import driver_cookie_jar_to_requests_cookies


class Credentials(NamedTuple):
    id: str
    pwd: str


async def fetch_credentials(op_client: op.OpSdkClient) -> Credentials:
    """Fetches credentials from my 1Password vault."""
    item = "Viseca One"
    username = await op_client.read(op.FINDATA_VAULT, item, "username")
    password = await op_client.read(op.FINDATA_VAULT, item, "password")
    return Credentials(id=username, pwd=password)


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


def fetch_latest_bill(driver: webdriver.remote.webdriver.WebDriver) -> bytes:
    driver.get('https://one.viseca.ch/de/rechnungen')
    driver.implicitly_wait(30)
    latest_bill_a_elem = driver.find_element(
        By.CSS_SELECTOR, '#statement-list-statement-date0 a')
    latest_bill_a_elem_id = latest_bill_a_elem.get_attribute('id')
    if not latest_bill_a_elem_id:
        raise Exception("Could not find the latest bill element's ID.")
    latest_bill_id = extract_bid(latest_bill_a_elem_id)
    return fetch_bill(latest_bill_id, driver.get_cookies())


def extract_bid(elem_id: str) -> str:
    m = re.match('statement-list-statement-url(.*)', elem_id)
    if not m:
        raise Exception("Could not extract the bill id from " + elem_id)
    return m[1]


def fetch_bill(bill_id: str, cookies) -> bytes:
    fetch_page = ('https://api.one.viseca.ch/v1/statement/' + bill_id +
                  '/document')
    response = requests.get(
        fetch_page, cookies=driver_cookie_jar_to_requests_cookies(cookies))
    if not response.ok:
        raise Exception("The statement fetch request has failed. " +
                        ('Response reason: {0}, parameters: {1}'
                         ).format(response.reason, (fetch_page, cookies)))
    return response.content


def fetch_data(creds: Credentials,
               driver: webdriver.remote.webdriver.WebDriver) -> bytes:
    """Fetches Viseca's transaction data using Selenium

    Returns:
        A PDF bytestream representing the latest statement.
    """
    login(creds, driver)
    wait_for_login(driver)
    return fetch_latest_bill(driver)
