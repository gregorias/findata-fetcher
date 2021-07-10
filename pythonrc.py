# A dev pythonrc module.
# I use this module for interactive debugging. It is automatically loaded
# in my (b)python setup and provides convenient bindings.
from selenium import webdriver
from seleniumwire import webdriver as webdriverwire
import email
import json
import requests

import fetcher.tool as t
from fetcher.driverutils import driver_cookie_jar_to_requests_cookies
from fetcher import bcge
from fetcher import bcgecc
from fetcher import cs
from fetcher import coop
from fetcher import degiro
from fetcher import finpension
from fetcher import ib
from fetcher import gmail

with open('config.json', 'r') as cf:
    config = json.load(cf)
    bcge_creds = t.extract_bcge_credentials(config)
    bcgecc_creds = t.extract_bcgecc_credentials(config)
    cs_creds = t.extract_cs_credentials(config)
    degiro_creds = t.extract_degiro_credentials(config)
    finpension_creds = t.extract_finpension_credentials(config)
    gmail_creds = t.extract_gmail_credentials(config)
    ib_creds = t.extract_ib_credentials(config)


def start_driver():
    driver = webdriver.Firefox()
    driver.implicitly_wait(20)
    return driver


def start_driver_wire():
    driver = webdriverwire.Firefox()
    driver.implicitly_wait(20)
    return driver
