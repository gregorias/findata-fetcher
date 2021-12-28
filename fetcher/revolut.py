# -*- coding: utf-8 -*-
"""Fetches account statements from Revolut"""
from typing import NamedTuple


class Credentials(NamedTuple):
    country_code: str
    phone_number: str
    pin: str
