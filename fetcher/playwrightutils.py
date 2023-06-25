"""A collection of utilities for working with Playwright."""

import asyncio
import contextlib
from enum import Enum
import os
import pathlib
import playwright.async_api
from playwright.async_api import async_playwright
import shutil
import time
import typing
from typing import TypedDict

from .contextextra import async_closing


class Browser(Enum):
    FIREFOX = 1
    CHROMIUM = 2
    WEBKIT = 3


def get_browser_type(
        pw: playwright.async_api.Playwright,
        browser_type: Browser) -> playwright.async_api.BrowserType:
    if browser_type == Browser.FIREFOX:
        return pw.firefox
    elif browser_type == Browser.CHROMIUM:
        return pw.chromium
    elif browser_type == Browser.WEBKIT:
        return pw.webkit
    raise Exception(f"Unknown browser type: {browser_type}")


def playwright_cookie_jar_to_requests_cookies(
        playwright_cookies: list[playwright.async_api.Cookie]) -> dict:
    """
    Transforms a cookie jar from Playwright into a Requests-compatible dict.

    :param playwright_cookies list[dict]
    :rtype dict
    """
    return {c['name']: c['value'] for c in playwright_cookies}


# Using an async context manager, because it's more natural:
# * The client can now define the timeout using an orthogonal asyncio.timeout
# * The client can combine it with other concurrent operations without
#   blocking.
@contextlib.asynccontextmanager
async def preserve_new_file(dir: pathlib.Path):
    """
    A context manager that preserves a file downloaded in a Playwright session.

    Playwright may asynchronously download a file. This context manager watches
    for this event and copies the file once it happens.

    :param dir pathlib.Path: The downloads directory used by Playwright.
    """
    old_dirs = set(os.listdir(dir))

    async def wait_for_new_file():
        while True:
            new_dirs = set(os.listdir(dir))
            if len(new_dirs) > len(old_dirs):
                new_files = new_dirs.difference(old_dirs)
                for nf in new_files:
                    # We need to copy the file, because playwright deletes
                    # downloaded files on browser close.
                    shutil.copy(dir / nf, dir / (nf + ".csv"))
                break
            else:
                await asyncio.sleep(1)
                continue

    wait_for_new_file_task = asyncio.create_task(wait_for_new_file())
    yield wait_for_new_file_task
    await wait_for_new_file_task


class Download:

    def __init__(self, download_info):
        self.download_info = download_info

    async def wait_for_download(self):
        download = await self.download_info.value
        download_path = await download.path()
        if not download_path:
            raise Exception("The download interception has failed.")
        with open(download_path, "rb") as f:
            self.value = f.read()

    def downloaded_content(self) -> bytes:
        """Returns the bytes of the downloaded file."""
        return self.value


@contextlib.asynccontextmanager
async def intercept_download(
        page: playwright.async_api.Page) -> typing.AsyncIterator[Download]:
    """An async context manager that waits for a download to finish.

    Returns the object representing the downloaded content."""
    async with page.expect_download() as download_info:
        download = Download(download_info)
        yield download
    await download.wait_for_download()


@contextlib.asynccontextmanager
async def new_page(
        browser_type: Browser,
        headless: bool = False
) -> typing.AsyncIterator[playwright.async_api.Page]:
    """Opens a new page in a new context.

    :param browser playwright.async_api.BrowserType: The browser to use.
    :param headless bool: Whether to run a fixed-viewport headless browser or a
    responsive one. Defaults to False.
    """
    async with (async_playwright() as pw,
                async_closing(
                    get_browser_type(pw,
                                     browser_type).launch(headless=headless))
                as browser,
                async_closing(browser.new_context(no_viewport=not headless)) as
                context, async_closing(context.new_page()) as page):
        yield page
