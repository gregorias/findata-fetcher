# A dev pythonrc module.
# I use this module for interactive debugging. It is automatically loaded
# in my (b)python setup and provides convenient bindings.
import asyncio
from bs4 import BeautifulSoup  # type: ignore
from enum import Enum
from selenium import webdriver
from selenium.webdriver.common.by import By  # type: ignore
from seleniumwire import webdriver as webdriverwire  # type: ignore
from playwright.async_api import async_playwright
import email
import json
import requests
import playwright

import fetcher.tool as t
from fetcher.driverutils import driver_cookie_jar_to_requests_cookies
from fetcher.playwrightutils import playwright_cookie_jar_to_requests_cookies
from fetcher import bcge
from fetcher import bcgecc
from fetcher import coop_supercard
from fetcher import cs
from fetcher import degiro
from fetcher import finpension
from fetcher import galaxus
from fetcher import gmail
from fetcher import ib
from fetcher import revolut
from fetcher import revolut_mail
from fetcher import splitwise
from fetcher import ubereats

with open('config.json', 'r') as cf:
    config = json.load(cf)
    bcge_creds = t.extract_bcge_credentials(config)
    bcgecc_creds = t.extract_bcgecc_credentials(config)
    cs_creds = t.extract_cs_credentials(config)
    degiro_creds = t.extract_degiro_credentials(config)
    finpension_creds = t.extract_finpension_credentials(config)
    gmail_creds = t.extract_gmail_credentials(config)
    ib_creds = t.extract_ib_credentials(config)
    revolut_creds = t.extract_revolut_credentials(config)
    revolut_account_numbers = config['revolut_account_numbers']
    supercard_creds = t.extract_supercard_credentials(config)
    splitwise_creds = t.extract_splitwise_credentials(config)


def start_driver():
    driver = webdriver.Firefox()
    driver.implicitly_wait(20)
    return driver


def start_driver_wire():
    driver = webdriverwire.Firefox()
    driver.implicitly_wait(20)
    return driver


class Browser(Enum):
    FIREFOX = 1
    CHROMIUM = 2


async def start_playwright(
    browser_spec: Browser = Browser.FIREFOX
) -> tuple[playwright.async_api.Playwright, playwright.async_api.Browser,
           playwright.async_api.Page]:
    """Starts a synchronous Playwright instance.

    :rtype tuple[playwright.async_api.Playwright,
                 playwright.async_api.Browser,
                 playwright.async_api.Page]
    """
    pw = await async_playwright().start()
    browser_type = pw.firefox if browser_spec == Browser.FIREFOX else pw.chromium
    browser = await browser_type.launch(
        headless=False, downloads_path="/Users/grzesiek/Downloads")
    p = await browser.new_page()
    return (pw, browser, p)
