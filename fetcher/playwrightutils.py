"""A collection of utilities for working with Playwright."""

import contextlib
import pathlib
import typing
from enum import Enum
from typing import Optional

import playwright.async_api
from playwright.async_api import async_playwright

from .contextextra import async_closing


class Browser(Enum):
    FIREFOX = 1
    CHROMIUM = 2
    WEBKIT = 3


def get_browser_type(
    pw: playwright.async_api.Playwright, browser_type: Browser
) -> playwright.async_api.BrowserType:
    if browser_type == Browser.FIREFOX:
        return pw.firefox
    elif browser_type == Browser.CHROMIUM:
        return pw.chromium
    elif browser_type == Browser.WEBKIT:
        return pw.webkit
    raise Exception(f"Unknown browser type: {browser_type}")


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
    page: playwright.async_api.Page,
) -> typing.AsyncIterator[Download]:
    """An async context manager that waits for a download to finish.

    Returns the object representing the downloaded content."""
    async with page.expect_download() as download_info:
        download = Download(download_info)
        yield download
    await download.wait_for_download()


@contextlib.asynccontextmanager
async def new_stack(
    browser_type: Browser,
    headless: bool = False,
    downloads_path: Optional[pathlib.Path] = None,
) -> typing.AsyncIterator[
    tuple[
        playwright.async_api.Playwright,
        playwright.async_api.Browser,
        playwright.async_api.BrowserContext,
        playwright.async_api.Page,
    ]
]:
    """Opens a new page in a new context.

    :param browser playwright.async_api.BrowserType: The browser to use.
    :param headless bool: Whether to run a fixed-viewport headless browser or a
    :param downloads_path Optional[pathlib.Path]: The path used for downloads.
    responsive one. Defaults to False.
    """
    async with (
        async_playwright() as pw,
        async_closing(
            await get_browser_type(pw, browser_type).launch(
                headless=headless, downloads_path=downloads_path
            )
        ) as browser,
        async_closing(await browser.new_context(no_viewport=not headless)) as context,
        async_closing(await context.new_page()) as page,
    ):
        yield (pw, browser, context, page)


@contextlib.asynccontextmanager
async def new_page(
    browser_type: Browser,
    headless: bool = False,
    downloads_path: Optional[pathlib.Path] = None,
) -> typing.AsyncIterator[playwright.async_api.Page]:
    """Opens a new page in a new context.

    :param browser playwright.async_api.BrowserType: The browser to use.
    :param headless bool: Whether to run a fixed-viewport headless browser or a
    :param downloads_path Optional[pathlib.Path]: The path used for downloads.
    responsive one. Defaults to False.
    """
    async with new_stack(browser_type, headless, downloads_path) as (_, _, _, page):
        yield page
