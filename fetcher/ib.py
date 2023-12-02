# -*- coding: utf-8 -*-
"""An interface for Interactive Brokers.

It's similar to fetcher.ib but uses Playwright instead of Selenium.
"""
import datetime
from decimal import Decimal
from enum import Enum
import pathlib
import re
from typing import NamedTuple
import playwright.async_api

from . import op
from .playwrightutils import get_new_files

IB_DOMAIN = 'https://www.interactivebrokers.co.uk'


class Credentials(NamedTuple):
    id: str
    pwd: str


def fetch_credentials() -> Credentials:
    """Fetches the credentials from my 1Password vault.

    This function blocks until the credentials are fetched.
    """
    username = op.read('Private', 'Interactive Brokers', 'username')
    password = op.read('Private', 'Interactive Brokers', 'password')
    return Credentials(id=username, pwd=password)


async def login(page: playwright.async_api.Page, creds: Credentials) -> None:
    """Logs into Interactive Brokers.

    Returns once the authentication process finishes. The page will contain
    Charles Schwab's dashboard.

    :param page playwright.async_api.Page: A blank page.
    :param creds Credentials
    :rtype None
    """
    await page.goto(f"{IB_DOMAIN}/sso/Login")
    await page.get_by_placeholder("Username").click()
    await page.get_by_placeholder("Username").fill(creds.id)
    await page.get_by_placeholder("Password").click()
    await page.get_by_placeholder("Password").fill(creds.pwd)
    await page.get_by_role("button", name="Login ").click()
    IB_KEY_COMBOBOX_OPTION = "5.2a"
    await page.get_by_role("combobox").select_option(IB_KEY_COMBOBOX_OPTION)
    await page.wait_for_url("https://www.interactivebrokers.co.uk/portal/**")


class DepositSource(Enum):
    """Available deposit sources.

    The value is the IB method name of the source.
    """
    CHARLES_SCHWAB = "Charles Schwab"
    BCGE = "Wire-BCGE"


class SourceBankDepositInformation(NamedTuple):
    transfer_to: str
    iban: str
    beneficiary_bank: str
    for_further_credit: str


async def deposit(page: playwright.async_api.Page, source: DepositSource,
                  amount: Decimal) -> SourceBankDepositInformation:
    """Initiates a deposit.

    :param page playwright.async_api.Page: A page in a logged in state.
    :param source DepositSource: The source of the deposit.
    :param amount Decimal: The amount to deposit.
    :rtype None
    """
    assert amount > 0, f"Must deposit a positive amount, got f{amount}."
    await page.goto(IB_DOMAIN + '/AccountManagement/AmAuthentication' +
                    '?action=FUND_TRANSFERS&type=DEPOSIT')
    await page.get_by_role("heading", name=source.value).click()
    await page.get_by_placeholder("Required").click()
    await page.keyboard.type(str(amount))
    await page.get_by_role("link", name="Get Transfer Instructions").click()

    # Wait for the instructions to appear.
    await page.get_by_text("Provide the following information" +
                           " to your bank to initiate the transfer.").click()

    #  await page.get_by_text("Transfer Funds to Beneficiary/Account Title"
    #                         ).click()
    async def extract_data_from_row(
            row: playwright.async_api.Locator) -> tuple[str, str]:
        labels = await row.locator('label').all()
        tmp = []
        for label in labels:
            text_content = await label.text_content()
            assert text_content, f"Expected a label f{label} to have text."
            tmp.append(text_content.strip())
        assert len(tmp) == 2, f"Expected two labels per row but got f{labels}."
        return (tmp[0], tmp[1])

    deposit_information_dict = {}

    all_rows = await page.locator("wire-destination wire-destination-bank .row"
                                  ).all()
    for row in all_rows:
        data_tuple = await extract_data_from_row(row)
        deposit_information_dict[data_tuple[0]] = data_tuple[1]

    for_further_benefit_row = page.locator(
        "wire-destination" + " destination-further-benefit-to .row").first
    for_further_benefit_tuple = await extract_data_from_row(
        for_further_benefit_row)
    deposit_information_dict[
        for_further_benefit_tuple[0]] = for_further_benefit_tuple[1]

    return SourceBankDepositInformation(
        transfer_to=deposit_information_dict[
            "Transfer Funds to Beneficiary/Account Title"],
        iban=deposit_information_dict[
            "International Bank Account Number (IBAN)"],
        beneficiary_bank=deposit_information_dict["Beneficiary Bank"],
        for_further_credit=deposit_information_dict[
            "Payment Reference/For Further Credit to"])


async def cancel_pending_deposits(page: playwright.async_api.Page) -> None:
    """
    Cancels all pending deposits.

    :param page playwright.async_api.Page: A page in a logged in state.
    :return: None
    """
    await page.goto(IB_DOMAIN + '/AccountManagement/AmAuthentication' +
                    '?action=TransactionHistory')
    # Wait for the list of transfers to load.
    await page.get_by_role(
        "row", name=re.compile(".*Deposit.*Bank Transfer.*")).first.focus()
    pending_deposits = await page.get_by_role(
        "row", name=re.compile(".*Deposit.*Pending.*")).all()
    for pending_deposit in pending_deposits:
        await pending_deposit.click()
        await page.get_by_role("link", name="Cancel Request").click()
        await page.get_by_role("link", name="Yes").click()
        # Wait for the cancellation to finish.
        await page.get_by_role(
            "heading", name='Your Deposit request has been cancelled').focus()
        await page.get_by_role("button", name="Close").click()


def quarter_ago(day: datetime.date) -> datetime.date:
    return day - datetime.timedelta(days=90)


async def fetch_account_statement(page: playwright.async_api.Page,
                                  download_dir: pathlib.Path) -> bytes:
    """Fetches Interactive Brokers's account statement.

    :param page playwright.async_api.Page: A page in a logged in state.
    :return bytes: The statement CSV file.
    """
    await page.goto(IB_DOMAIN + '/AccountManagement/AmAuthentication' +
                    '?action=Statements')
    # Click the right arrow that goes to the dialog for the account statement.
    await (page.get_by_role("paragraph").filter(has_text="MTM Summary")
           # An XPath that selects the first parent that a class "row"
           .locator("//ancestor::div[contains(@class, 'row')]").last.locator(
               "a.btn-icon .fa-circle-arrow-right").click())
    await page.locator("div.row", has_text="Period").last.get_by_role(
        'combobox').select_option("string:DATE_RANGE")

    today = datetime.date.today()
    quarter_ago_str = quarter_ago(today).strftime("%Y-%m-%d")
    for _ in range(2):
        # For some reason, doing it only once doesn't work.
        await page.locator("input[name=\"fromDate\"]").fill(quarter_ago_str)
        await page.keyboard.press("Enter")

    async with get_new_files(download_dir) as files_downloaded_event:
        await (page.locator(".row", has_text='CSV').last.locator(
            "a", has_text="Download").first.click())
        await files_downloaded_event

    for statement_filename in await files_downloaded_event:
        with open(statement_filename, 'rb') as f:
            return f.read()
    raise Exception("Expected to download a statement but didn't.")
