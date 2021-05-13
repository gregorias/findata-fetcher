# -*- coding: utf-8 -*-
"""Fetches account statement from Degiro"""
from datetime import date, timedelta
from typing import NamedTuple
import logging

from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore
from selenium.webdriver.support import expected_conditions  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
import requests

from .driverutils import driver_cookie_jar_to_requests_cookies


class Credentials(NamedTuple):
    id: str
    pwd: str


def login(creds: Credentials,
          driver: webdriver.remote.webdriver.WebDriver) -> None:
    logging.info("Logging in.")
    LOGIN_PAGE = 'https://trader.degiro.nl/login/chde/#/login'
    driver.get(LOGIN_PAGE)
    driver.find_element(By.ID, "username").send_keys(creds.id + Keys.TAB)
    driver.find_element(By.ID, "password").send_keys(creds.pwd + Keys.RETURN)


def wait_for_login(driver: webdriver.remote.webdriver.WebDriver):
    logging.info("Waiting for login.")
    wait = WebDriverWait(driver, 30)
    wait.until(
        expected_conditions.url_to_be(
            'https://trader.degiro.nl/trader/#/markets'))


def fetch_csv(url: str, cookies) -> bytes:
    headers = {
        'user-agent': ('Mozilla/5.0 (X11; Linux x86_64; rv:84.0) ' +
                       'Gecko/20100101 Firefox/84.0'),
    }
    response = requests.get(url, headers=headers, cookies=cookies)
    if not response.ok:
        raise Exception("The URL fetch request has failed. " +
                        ('Response reason: {0}, parameters: {1}'
                         ).format(response.reason, (url, cookies)))
    return response.content


def get_account_overview_url(from_date: date, to_date: date) -> str:
    date_format = "%Y-%m-%d"
    return (
        'https://trader.degiro.nl/trader/#/account-overview' +
        '?fromDate={from_date:s}&toDate={to_date:s}&aggregateCashFunds=true' +
        '&currency=All').format(
            from_date=from_date.strftime(date_format),
            to_date=to_date.strftime(date_format),
        )


def get_three_months_ago(start_date: date) -> date:
    return start_date - timedelta(93)


def fetch_account(driver: webdriver.remote.webdriver.WebDriver) -> bytes:
    logging.info("Fetching account.")
    driver.get(
        get_account_overview_url(
            from_date=get_three_months_ago(date.today()),
            to_date=date.today(),
        ))
    exportButton = driver.find_element(By.CSS_SELECTOR,
                                       '[data-name="exportButton"]')
    exportButton.click()
    reportExportForm = driver.find_element(By.CSS_SELECTOR,
                                           '[data-name="reportExportForm"]')
    csvLink = reportExportForm.find_element(
        By.XPATH, "//a[normalize-space(text()) = 'CSV']")
    csvFetchUrl = csvLink.get_attribute('href')
    cookies = driver_cookie_jar_to_requests_cookies(driver.get_cookies())
    return fetch_csv(csvFetchUrl, cookies)


def fetch_portfolio(driver: webdriver.remote.webdriver.WebDriver) -> bytes:
    logging.info("Fetching portfolio.")
    portfolioSideBarLink = driver.find_element(By.CSS_SELECTOR,
                                               '[href="#/portfolio"]')
    portfolioSideBarLink.click()
    exportButton = driver.find_element(By.CSS_SELECTOR,
                                       '[data-name="exportButton"]')
    exportButton.click()
    reportExportForm = driver.find_element(By.CSS_SELECTOR,
                                           '[data-name="reportExportForm"]')
    csvLink = reportExportForm.find_element(
        By.XPATH, "//a[normalize-space(text()) = 'CSV']")
    csvFetchUrl = csvLink.get_attribute('href')
    cookies = driver_cookie_jar_to_requests_cookies(driver.get_cookies())
    return fetch_csv(csvFetchUrl, cookies)


def fetch_account_statement(driver: webdriver.remote.webdriver.WebDriver,
                            creds: Credentials) -> bytes:
    """Fetches Degiro's account statement using Selenium

    Returns:
        A CSV UTF-8 encoded statement.
    """
    driver.implicitly_wait(30)
    login(creds, driver)
    wait_for_login(driver)
    return fetch_account(driver)


def fetch_portfolio_statement(creds: Credentials) -> bytes:
    """Fetches Degiro's portfolio statement using Selenium

    Returns:
        A CSV UTF-8 encoded statement.
    """
    with webdriver.Firefox() as driver:
        driver.implicitly_wait(30)
        login(creds, driver)
        wait_for_login(driver)
        return fetch_portfolio(driver)
