# A dev pythonrc module.
# I use this module for interactive debugging. It is automatically loaded
# in my (b)python setup and provides convenient bindings.
#
# Example session:
#
# >>> p = start()
# >>> op = ruc(connect_op())
# >>> bcge_creds = ruc(fetcher.bcgecc.fetch_credentials(op))
# >>> import fetcher.revolut as r
# >>> ruc(r.login(p))
import asyncio
import atexit
import decimal
import json
import pathlib
import re  # noqa: F401

import playwright
import playwright.async_api
from playwright.async_api import async_playwright

import fetcher.bcgecc as bcgecc  # noqa: F401
import fetcher.revolut as revolut  # noqa: F401
import fetcher.tool as t
from fetcher import op  # noqa: F401
from fetcher.playwrightutils import (
    Browser,
    get_browser_type,
)
from fetcher.tool import connect_op  # noqa: F401

D = decimal.Decimal

with open(t.FETCHER_CONFIG_DEFAULT, 'r') as cf:
    config = json.load(cf)
    revolut_currencies = config['revolut_currencies']

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


def start():
    pw, b, bc, p = ruc(start_playwright())
    return p


async def open_1password_client() -> op.OpSdkClient:
    return await op.OpSdkClient.connect(op.fetch_service_account_auth_token())
