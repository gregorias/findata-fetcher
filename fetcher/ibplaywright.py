# -*- coding: utf-8 -*-
"""An interface for Interactive Brokers.

It's similar to fetcher.ib but uses Playwright instead of Selenium.
"""
from decimal import Decimal
from enum import Enum
from typing import NamedTuple
import playwright.async_api

from .ib import Credentials

D = Decimal


async def login(page: playwright.async_api.Page, creds: Credentials) -> None:
    """Logs into Interactive Brokers.

    Returns once the authentication process finishes. The page will contain
    Charles Schwab's dashboard.

    :param page playwright.async_api.Page: A blank page.
    :param creds Credentials
    :rtype None
    """
    await page.goto("https://www.interactivebrokers.co.uk/sso/Login")
    await page.get_by_placeholder("Username").click()
    await page.get_by_placeholder("Username").fill(creds.id)
    await page.get_by_placeholder("Password").click()
    await page.get_by_placeholder("Password").fill(creds.pwd)
    await page.get_by_role("button", name="Login ").click()
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
    await page.goto('https://www.interactivebrokers.co.uk' +
                    '/AccountManagement/AmAuthentication' +
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
