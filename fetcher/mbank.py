"""Fetches account data from mBank"""
from typing import NamedTuple
import datetime
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


def transform_and_strip_mbanks_csv(raw_csv: bytes) -> bytes:
    raw_csv = raw_csv[raw_csv.find(b'#Data'):]
    csv = raw_csv.decode('cp1250')
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
    return transform_and_strip_mbanks_csv(csv)
