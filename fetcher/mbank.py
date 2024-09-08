"""Fetches account data from mBank"""
import datetime
from typing import NamedTuple

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from . import op
from .driverutils import driver_cookie_jar_to_requests_cookies, format_date


class Credentials(NamedTuple):
    id: str
    pwd: str


async def fetch_credentials(op_client: op.OpSdkClient) -> Credentials:
    """Fetches credentials from my 1Password vault."""
    item = "mbank.pl"
    username = await op_client.read(op.FINDATA_VAULT, item, "username")
    password = await op_client.read(op.FINDATA_VAULT, item, "password")
    return Credentials(id=username, pwd=password)


MBANK_LOGIN_PAGE = 'https://online.mbank.pl/pl/Login/history'
HISTORY_PAGE = 'https://online.mbank.pl/history'
FETCH_PAGE = (
    'https://online.mbank.pl/pl/Pfm/HistoryApi/GetPfmTransactionsSummary')


def download_request_json_payload(from_date: datetime.date,
                                  to_date: datetime.date) -> dict:
    """Generates a payload for Mbank's download request"""
    return {
        "saveFileType": "CSV",
        "pfmFilters": {
            "productIds": "399116",
            "amountFrom": None,
            "amountTo": None,
            "useAbsoluteSearch": False,
            "currency": "",
            "categories": "",
            "operationTypes": "",
            "searchText": "",
            "dateFrom": format_date(from_date),
            "dateTo": format_date(to_date),
            "standingOrderId": "",
            "showDebitTransactionTypes": False,
            "showCreditTransactionTypes": False,
            "showIrrelevantTransactions": True,
            "showSavingsAndInvestments": True,
            "saveShowIrrelevantTransactions": False,
            "saveShowSavingsAndInvestments": False,
            "selectedSuggestionId": "",
            "selectedSuggestionType": "",
            "showUncategorizedTransactions": False,
            "debitCardNumber": "",
            "showBalance": True,
            "counterpartyAccountNumbers": "",
            "sortingOrder": "ByDate",
            "tags": []
        }
    }


def check_decoding(bs: bytes, encoding: str) -> bool:
    try:
        bs.decode(encoding)
        return True
    except UnicodeDecodeError:
        return False


def transform_and_strip_mbanks_csv(raw_csv: bytes) -> bytes:
    if check_decoding(raw_csv, 'utf-8'):
        csv = raw_csv.decode('utf-8')
    else:
        csv = raw_csv.decode('cp1250')
    csv = csv[csv.find('#Data'):]
    csv = csv.replace('\r\n', '\n')
    # Remove two newlines at the end
    csv = csv[:-2]
    return csv.encode('utf-8')


def login_to_mbank(creds: Credentials,
                   driver: webdriver.remote.webdriver.WebDriver) -> None:
    driver.get(MBANK_LOGIN_PAGE)
    driver.find_element(By.ID, "userID").send_keys(creds.id + Keys.TAB)
    driver.find_element(By.ID, "pass").send_keys(creds.pwd + Keys.RETURN)
    wait = WebDriverWait(driver, 30)
    wait.until(
        expected_conditions.element_to_be_clickable(
            (By.CSS_SELECTOR,
             '[data-test-id="SCA:UnknownDevice:OneTimeAccess"]'))).click()
    wait = WebDriverWait(driver, 30)
    wait.until(expected_conditions.url_matches(HISTORY_PAGE))


def fetch_all_transactions_since_2018(
        driver: webdriver.remote.webdriver.WebDriver) -> bytes:
    from_date = datetime.date(2018, 1, 1)
    to_date = datetime.date.today()
    resp = requests.post(
        FETCH_PAGE,
        json=download_request_json_payload(from_date, to_date),
        cookies=driver_cookie_jar_to_requests_cookies(driver.get_cookies()))
    if not resp.ok:
        raise Exception(
            "The CSV fetch request has failed. Response reason: {0}".format(
                resp.reason))
    return resp.content


def fetch_mbank_data(driver: webdriver.remote.webdriver.WebDriver,
                     creds: Credentials) -> bytes:
    """Fetches Mbank's transaction data using Selenium

    Returns:
        A CSV UTF-8 encoded string with the fetched transactions.
    """
    login_to_mbank(creds, driver)
    csv = fetch_all_transactions_since_2018(driver)
    with open('/Users/grzesiek/Downloads/example.csv', 'wb') as f:
        f.write(csv)
    return transform_and_strip_mbanks_csv(csv)
