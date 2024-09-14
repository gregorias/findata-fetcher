# A dev pythonrc module.
# I use this module for interactive debugging. It is automatically loaded
# in my (b)python setup and provides convenient bindings.
import asyncio
import atexit
import decimal
import json
import pathlib

import playwright
from playwright.async_api import async_playwright
from selenium import webdriver

import fetcher.tool as t
from fetcher import op  # noqa: F401
from fetcher.playwrightutils import (
    Browser,
    get_browser_type,
)

D = decimal.Decimal

with open(t.FETCHER_CONFIG_DEFAULT, 'r') as cf:
    config = json.load(cf)
    revolut_account_numbers = config['revolut_account_numbers']


def start_driver():
    driver = webdriver.Firefox()
    driver.implicitly_wait(20)
    return driver


loop = asyncio.new_event_loop()
atexit.register(loop.close)


def ruc(a):
    return loop.run_until_complete(a)


async def start_playwright(
    browser_spec: Browser = Browser.FIREFOX
) -> tuple[playwright.async_api.Playwright, playwright.async_api.Browser,
           playwright.async_api.BrowserContext, playwright.async_api.Page]:
    """Starts a synchronous Playwright instance.

    :rtype tuple[playwright.async_api.Playwright,
                 playwright.async_api.Browser,
                 playwright.async_api.Page]
    """
    downloads_dir = pathlib.Path.home().joinpath('Downloads')

    pw = await async_playwright().start()
    browser_type = get_browser_type(pw, browser_spec)
    browser = await browser_type.launch(headless=False,
                                        downloads_path=downloads_dir)
    # no_viewport=True disables the default fixed viewport and lets the site
    # adapt to the actual window size
    context = await browser.new_context(no_viewport=True)
    p = await context.new_page()
    return (pw, browser, context, p)


op_client = ruc(op.OpSdkClient.connect(op.fetch_service_account_auth_token()))
