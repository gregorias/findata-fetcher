"""A collection of utilities for working with Playwright."""

from typing import TypedDict
import playwright.sync_api


def playwright_cookie_jar_to_requests_cookies(
        playwright_cookies: list[playwright.sync_api.Cookie]) -> dict:
    """
    Transforms a cookie jar from Playwright into a Requests-compatible dict.

    :param playwright_cookies list[dict]
    :rtype dict
    """
    return {c['name']: c['value'] for c in playwright_cookies}
