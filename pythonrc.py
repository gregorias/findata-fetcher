# A dev pythonrc module.
# I use this module for interactive debugging. It is automatically loaded
# in my (b)python setup and provides convenient bindings.
from selenium import webdriver
import json

import fetcher.tool as t
from fetcher import bcge
from fetcher import degiro
from fetcher import ib

with open('config.json', 'r') as cf:
    config = json.load(cf)
    bcge_creds = t.extract_bcge_credentials(config)
    cs_creds = t.extract_cs_credentials(config)
    degiro_creds = t.extract_degiro_credentials(config)
    ib_creds = t.extract_ib_credentials(config)


def start_driver():
    driver = webdriver.Firefox()
    driver.implicitly_wait(20)
    return driver
