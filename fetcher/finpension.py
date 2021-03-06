# -*- coding: utf-8 -*-
import time
from typing import NamedTuple

from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
from selenium.webdriver.support import expected_conditions  # type: ignore

from .driverutils import set_value
from . import gmail


class Credentials(NamedTuple):
    id: str
    pwd: str


def login(creds: Credentials,
          driver: webdriver.remote.webdriver.WebDriver) -> None:
    LOGIN_PAGE = 'https://app.finpension.ch/login'
    driver.get(LOGIN_PAGE)
    phone_country_selection = driver.find_element(By.CSS_SELECTOR,
                                                  ".PhoneInputCountrySelect")
    set_value(driver, phone_country_selection, 'CH')
    wait = WebDriverWait(driver, 30)
    mobile_number_field = wait.until(
        expected_conditions.element_to_be_clickable((By.ID, 'mobile_number')))
    password_field = wait.until(
        expected_conditions.element_to_be_clickable((By.NAME, 'password')))
    mobile_number_field.send_keys(creds.id + Keys.TAB)
    password_field.send_keys(creds.pwd + Keys.RETURN)
    code_field = wait.until(
        expected_conditions.element_to_be_clickable(
            (By.CSS_SELECTOR, 'ion-input[name=code]')))
    code_field.click()


def wait_for_login(driver: webdriver.remote.webdriver.WebDriver) -> None:
    wait = WebDriverWait(driver, 30)
    wait.until(
        expected_conditions.url_matches('https://app.finpension.ch/portfolio'))


def mail_transactions(driver: webdriver.remote.webdriver.WebDriver) -> None:
    driver.get('https://app.finpension.ch/documents/transactions')
    wait = WebDriverWait(driver, 30)
    mail_the_csv_button = wait.until(
        expected_conditions.element_to_be_clickable(
            (By.CSS_SELECTOR, 'ion-icon.ux-documents-item__mail')))
    mail_the_csv_button.click()


def fetch_csv_from_gmail(creds: gmail.Credentials) -> bytes:
    with gmail.connect(creds) as imap:
        for i in range(10):
            mail_nos = gmail.search_for_inbox_mails(imap,
                                                    'Transaktions-Report')
            if not mail_nos:
                time.sleep(1)
        if not mail_nos:
            raise Exception("Could not find the Finpension report mail.")
        report_no = mail_nos[0]
        msg = gmail.fetch_mail(imap, report_no)
        csv_part = list(msg.walk())[2]
        _, csv_content = gmail.fetch_file(csv_part)
        gmail.archive_mail(imap, report_no)
        return csv_content


def fetch_data(creds: Credentials, gmail_creds: gmail.Credentials,
               driver: webdriver.remote.webdriver.WebDriver) -> bytes:
    """Fetches Finpensions' transaction data.

    Returns:
        A CSV UTF-8 encoded string with the fetched transactions.
    """
    driver.implicitly_wait(30)
    login(creds, driver)
    wait_for_login(driver)
    time.sleep(2)
    mail_transactions(driver)
    return fetch_csv_from_gmail(gmail_creds)
