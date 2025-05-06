"""A collection of data processing utilities for interaction with websites"""
import datetime
from typing import Dict, List


def format_date(date: datetime.date) -> str:
    """Formats a date into a string download request"""
    return date.strftime("%Y-%m-%dT00:00:00.000Z")


def driver_cookie_jar_to_requests_cookies(driver_cookies: List[Dict]) -> Dict:
    return {c['name']: c['value'] for c in driver_cookies}
