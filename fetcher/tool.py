# -*- coding: utf-8 -*-
"""
Fetch my accounting data into a CSV file.

Usage: python -m fetcher.tool --help
"""

import asyncio
import contextlib
from contextlib import contextmanager
import csv
import datetime
import decimal
import functools
import json
import logging
from os import path
from pathlib import Path, PurePath
import tempfile
import typing
import shutil
import sys

from selenium import webdriver  # type: ignore
from selenium.webdriver.firefox.service import Service as FirefoxService  # type: ignore
from seleniumwire import webdriver as webdriverwire  # type: ignore
from playwright.async_api import async_playwright
import click

from . import bcge
from . import bcgecc
from . import coop_supercard
from . import cs
from . import degiro
from . import easyride
from . import finpension
from . import galaxus
from . import gmail
from . import ib
from . import mbank
from . import patreon
from . import revolut
from . import revolut_mail
from . import splitwise
from . import ubereats

LOGGING_FILE_CFG_KEY = 'logging_file'


def getFirefoxDriver(logging=False) -> webdriver.Firefox:
    if logging:
        return webdriver.Firefox()
    else:
        service = FirefoxService(log_path=path.devnull)
        return webdriver.Firefox(service=service)


@contextmanager
def open_and_save_on_success(file, mode):
    try:
        with tempfile.NamedTemporaryFile(delete=False, mode=mode) as f:
            yield f
            fn = f.name
    except:
        raise
    else:
        shutil.move(fn, file)


@click.group()
@click.option('--config_file',
              default='config.json',
              type=click.File(mode='r'),
              help='The file containing the program\'s config')
@click.pass_context
def cli(ctx, config_file):
    config = json.load(config_file)
    assert isinstance(config, dict)

    ctx.obj['config'] = config

    if config[LOGGING_FILE_CFG_KEY]:
        logging.basicConfig(filename=config[LOGGING_FILE_CFG_KEY],
                            level=logging.DEBUG)
    stderr = logging.StreamHandler()
    stderr.setLevel(logging.WARNING)
    logging.getLogger('').addHandler(stderr)


def read_config_from_context(ctx):
    return ctx.obj['config']


@cli.command()
@click.pass_context
def pull_bcge(ctx) -> None:
    """Fetches BCGE data into a CSV file."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config['download_directory'])
    with getFirefoxDriver() as driver:
        sys.stdout.buffer.write(
            bcge.fetch_bcge_data(driver, extract_bcge_credentials(config)))


@cli.command()
@click.pass_context
def pull_bcgecc(ctx) -> None:
    """Fetches BCGE CC data and outputs a PDF."""
    config = read_config_from_context(ctx)
    with getFirefoxDriver() as driver:
        sys.stdout.buffer.write(
            bcgecc.fetch_data(extract_bcgecc_credentials(config), driver))


@cli.command()
@click.pass_context
def pull_coop_supercard(ctx) -> None:
    """Fetches Coop receipt PDFs from supercard.ch.

    This command saves the PDFs in the download directory.
    """
    config = ctx.obj['config']
    service = FirefoxService(log_path=path.devnull)
    opts = webdriver.FirefoxOptions()
    opts.add_argument('-headless')
    with webdriver.Firefox(options=opts, service=service) as driver:
        coop_supercard.fetch_and_save_receipts(
            driver,
            extract_supercard_credentials(config),
            Path(config['supercard_last_bc_file']),
            Path(config['download_directory']),
        )


@cli.command()
@click.pass_context
@click.option('--amount', required=True)
@click.argument('wire_instructions_csv', type=click.File('r'))
def cs_send_wire_to_ib(ctx, amount: str,
                       wire_instructions_csv: typing.TextIO) -> None:
    """Sends a wire transfor to Interactive Brokers.

    Example use:

        cs-send-wire-to-ib --amount=21.37 WIRE_INSTRUCTIONS_CSV
    """
    config = read_config_from_context(ctx)
    ffc_config = config['cs_ib_for_further_credit_instructions']

    wire_instructions_ib = ib.wire_instructions(
        decode_ib_wire_instructions(wire_instructions_csv))
    wire_instructions_cs = cs.WireInstructions(
        amount=amount,
        bank_routing_number=wire_instructions_ib.aba_routing_number,
        beneficiary_account_number=wire_instructions_ib.bank_account_number,
        for_further_credit=cs.ForFurtherCreditInstructions(
            account_number=ffc_config['account_number'],
            address=ffc_config['address'],
            city_and_state=ffc_config['city_and_state'],
            country=ffc_config['country'],
            name=ffc_config['name'],
            notes=ffc_config['notes'],
        ),
    )

    async def run():
        async with async_playwright() as pw:
            browser = await pw.firefox.launch(headless=False)
            page = await browser.new_page()
            await cs.send_wire_to_ib(page, extract_cs_credentials(config),
                                     wire_instructions_cs)
            await page.pause()
            await browser.close()

    asyncio.run(run())


@cli.command()
@click.option(
    '--download-directory',
    required=True,
    help='The target download directory.',
    type=click.Path(exists=True, file_okay=False, writable=True),
)
@click.pass_context
def pull_cs_account_history(ctx, download_directory) -> None:
    """Downloads Charles Schwab transaction history into a CSV file.

    This command places the downloaded file in a preconfigured directory.
    """
    config = read_config_from_context(ctx)
    download_directory = Path(download_directory)

    async def run():
        async with async_playwright() as pw:
            browser = await pw.firefox.launch(
                headless=False, downloads_path=download_directory)
            await cs.download_transaction_history(
                await browser.new_page(), extract_cs_credentials(config),
                download_directory)
            await browser.close()

    asyncio.run(run())


@cli.command()
@click.pass_context
def pull_degiro_account(ctx) -> None:
    """Fetches Degiro's account statement into a CSV file."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config['download_directory'])
    with getFirefoxDriver() as driver:
        pull_degiro_account_statement_helper(driver, download_directory,
                                             config)


def pull_degiro_account_statement_helper(
        driver: webdriver.remote.webdriver.WebDriver,
        download_directory: PurePath, config: dict) -> None:
    with open_and_save_on_success(download_directory / 'degiro-account.csv',
                                  'wb') as f:
        f.write(
            degiro.fetch_account_statement(driver,
                                           extract_degiro_credentials(config)))


@cli.command()
@click.pass_context
def pull_degiro_portfolio(ctx) -> None:
    """Fetches Degiro's portfolio statement and outputs a CSV file."""
    config = read_config_from_context(ctx)
    with getFirefoxDriver() as driver:
        sys.stdout.buffer.write(
            degiro.fetch_portfolio_statement(
                driver, extract_degiro_credentials(config)))


@cli.command()
@click.pass_context
def pull_easyride_receipts(ctx) -> None:
    """Fetches EasyRide receipt PDFs."""
    config = ctx.obj['config']
    easyride.fetch_and_archive_receipts(
        extract_gmail_credentials(config),
        PurePath(config['download_directory']),
    )


@cli.command()
@click.pass_context
def pull_finpension(ctx) -> None:
    """Prints Finpension's portfolio total.

    It will print a line with the value like "12123.12\n"."""
    config = read_config_from_context(ctx)

    async def run():
        async with async_playwright() as pw:
            browser = await pw.firefox.launch(headless=False)
            page = await browser.new_page()
            await finpension.login(page,
                                   extract_finpension_credentials(config))
            value = await finpension.fetch_current_total(page)
            print(value)

    asyncio.run(run())


def decode_ib_wire_instructions(csvf: typing.TextIO) -> dict[str, str]:
    """
    Decodes IB wire instructions

    :param csv typing.TextIO
    :rtype dict[str, str]
    """
    result = dict()
    for row in csv.DictReader(csvf):
        result[row['key']] = row['value']
    return result


@cli.command()
@click.pass_context
@click.option('--source',
              required=True,
              type=click.Choice(['CS', 'BCGE'], case_sensitive=False))
@click.option('--amount', required=True)
def ib_set_up_incoming_deposit(ctx, source, amount) -> None:
    """Sets up an incoming deposit on Interactive Brokers.

    Outputs a CSV with wire instructions.

    Example use:

        ib-set-up-incoming-deposit --source=cs --amount=21.37
    """
    config = read_config_from_context(ctx)
    service = FirefoxService(log_path=path.devnull)
    with getFirefoxDriver() as driver:
        driver.implicitly_wait(20)
        ib.login(driver, extract_ib_credentials(config))
        ib_source = (ib.DepositSource.BCGE
                     if source == 'BCGE' else ib.DepositSource.CHARLES_SCHWAB)
        instructions = ib.set_up_incoming_deposit(driver, ib_source,
                                                  decimal.Decimal(amount))
        writer = csv.DictWriter(sys.stdout,
                                fieldnames=["key", "value"],
                                delimiter=',')
        writer.writeheader()
        for key, value in instructions.items():
            writer.writerow({
                'key': key,
                'value': value,
            })


@cli.command()
@click.pass_context
def pull_ib(ctx) -> None:
    """Pulls Interactive Brokers CSV file statement."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config['download_directory'])
    service = FirefoxService(log_path=path.devnull)
    # We need to use webdriverwire, because we need access to the `requests`
    # API.
    with webdriverwire.Firefox(service=service) as driver:
        sys.stdout.buffer.write(
            ib.fetch_data(driver, extract_ib_credentials(config)))


@cli.command()
@click.pass_context
def pull_mbank(ctx) -> None:
    """Fetches mBank's data and outputs a CSV file."""
    config = read_config_from_context(ctx)
    with getFirefoxDriver() as driver:
        sys.stdout.buffer.write(
            mbank.fetch_mbank_data(driver, extract_mbank_credentials(config)))


def pull_mbank_helper(driver: webdriver.remote.webdriver.WebDriver,
                      download_directory: PurePath, config: dict) -> None:
    with open_and_save_on_success(download_directory / 'mbank.csv', 'wb') as f:
        f.write(
            mbank.fetch_mbank_data(driver, extract_mbank_credentials(config)))


@cli.command()
@click.option(
    '--download-directory',
    required=True,
    help='The target download directory.',
    type=click.Path(exists=True, file_okay=False, writable=True),
)
@click.pass_context
def pull_revolut(ctx, download_directory) -> None:
    """Fetches Revolut data into CSV files."""
    config = read_config_from_context(ctx)
    download_directory = Path(download_directory)

    async def run():
        async with asyncio.timeout(80):
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=False, downloads_path=download_directory)
                await revolut.download_statements(
                    await browser.new_page(), download_directory,
                    extract_revolut_credentials(config),
                    config['revolut_account_numbers'])
                await browser.close()

    asyncio.run(run())


@cli.command()
@click.pass_context
def pull_revolut_mail(ctx) -> None:
    """Fetches Revolut statements shared through gmail."""
    config = ctx.obj['config']
    revolut_mail.fetch_and_archive_statements(
        extract_gmail_credentials(config),
        PurePath(config['download_directory']),
    )


@cli.command()
@click.pass_context
def pull_splitwise(ctx) -> None:
    """Fetches the Splitwise statement."""
    config = ctx.obj['config']
    creds = extract_splitwise_credentials(config)
    csv = splitwise.export_balances_to_csv(splitwise.fetch_balances(creds))
    sys.stdout.buffer.write(csv)


@cli.command()
@click.pass_context
def pull_galaxus(ctx) -> None:
    """Fetches Digitec-Galaxus receipts in text format."""
    config = ctx.obj['config']
    download_directory = PurePath(config['download_directory'])
    gmail_creds = extract_gmail_credentials(config)
    with contextlib.closing(gmail.connect(gmail_creds)) as inbox:
        for bill in galaxus.fetch_and_archive_bills(inbox):
            with open(download_directory / (bill.subject + '.galaxus'),
                      'w') as f:
                f.write(bill.payload)


@cli.command()
@click.pass_context
def pull_patreon(ctx) -> None:
    """Fetches Patreon receipts in text format."""
    config = ctx.obj['config']
    patreon.fetch_and_archive_receipts(
        extract_gmail_credentials(config),
        PurePath(config['download_directory']),
    )


@cli.command()
@click.pass_context
def pull_uber_eats(ctx) -> None:
    """Fetches Uber Eats receipts in text format."""
    config = ctx.obj['config']
    download_dir = PurePath(config['download_directory'])
    for (title, content) in ubereats.fetch_and_archive_bills(
            extract_gmail_credentials(config)):
        with open(download_dir / (title + '.ubereats'), 'w') as f:
            f.write(content)


def extract_bcge_credentials(config: dict) -> bcge.Credentials:
    return bcge.Credentials(id=config['bcge_id'], pwd=config['bcge_pwd'])


def extract_bcgecc_credentials(config: dict) -> bcgecc.Credentials:
    return bcgecc.Credentials(id=config['bcgecc_id'], pwd=config['bcgecc_pwd'])


def extract_cs_credentials(config: dict) -> cs.Credentials:
    return cs.Credentials(id=config['cs_id'], pwd=config['cs_pwd'])


def extract_degiro_credentials(config: dict) -> degiro.Credentials:
    return degiro.Credentials(id=config['degiro_id'], pwd=config['degiro_pwd'])


def extract_finpension_credentials(config: dict) -> finpension.Credentials:
    return finpension.Credentials(phone_number=config['finpension_id'],
                                  password=config['finpension_pwd'])


def extract_ib_credentials(config: dict) -> ib.Credentials:
    return ib.Credentials(id=config['ib_id'], pwd=config['ib_pwd'])


def extract_gmail_credentials(config: dict) -> gmail.Credentials:
    return gmail.Credentials(id=config['gmail_id'], pwd=config['gmail_pwd'])


def extract_mbank_credentials(config: dict) -> mbank.Credentials:
    return mbank.Credentials(id=config['mbank_id'], pwd=config['mbank_pwd'])


def extract_revolut_credentials(config: dict) -> revolut.Credentials:
    return revolut.Credentials(country_code=config['revolut_country_code'],
                               phone_number=config['revolut_phone_number'],
                               pin=config['revolut_pin'])


def extract_supercard_credentials(config: dict) -> coop_supercard.Credentials:
    return coop_supercard.Credentials(id=config['supercard_id'],
                                      pwd=config['supercard_pwd'])


def extract_splitwise_credentials(config: dict) -> splitwise.Credentials:
    return splitwise.Credentials(
        consumer_key=config['splitwise_consumer_key'],
        consumer_secret=config['splitwise_consumer_secret'],
        api_key=config['splitwise_api_key'])


def main():
    cli(obj={})


if __name__ == '__main__':
    main()
