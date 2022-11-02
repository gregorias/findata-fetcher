# A dev pythonrc module.
# I use this module for interactive debugging. It is automatically loaded
# in my (b)python setup and provides convenient bindings.
from bs4 import BeautifulSoup  # type: ignore
from selenium import webdriver
from selenium.webdriver.common.by import By  # type: ignore
from seleniumwire import webdriver as webdriverwire  # type: ignore
from playwright.sync_api import sync_playwright
import email
import json
import requests
import playwright

import fetcher.tool as t
from fetcher.driverutils import driver_cookie_jar_to_requests_cookies
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


def start_playwright(
) -> tuple[playwright.sync_api.Playwright, playwright.sync_api.Browser,
           playwright.sync_api.Page]:
    """Starts a synchronous Playwright instance.

    :rtype tuple[playwright.sync_api.Playwright, playwright.sync_api.Browser]
    """
    pw = sync_playwright().start()
    browser = pw.firefox.launch(headless=False,
                                downloads_path="/Users/grzesiek/Downloads")
    p = browser.new_page()
    return (pw, browser, p)
