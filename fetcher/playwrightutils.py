"""A collection of utilities for working with Playwright."""

import asyncio
import contextlib
import os
import pathlib
import playwright.async_api
import shutil
import time
from typing import TypedDict


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
    yield None
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
