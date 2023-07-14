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
import os
from pathlib import Path, PurePath
import tempfile
import typing
import shutil
import sys

from selenium import webdriver  # type: ignore
from selenium.webdriver.firefox.service import Service as FirefoxService  # type: ignore
from seleniumwire import webdriver as webdriverwire  # type: ignore
from playwright.async_api import async_playwright

pw = async_playwright
import click

from . import bcge
from . import bcgecc
from . import coop_supercard
from .contextextra import async_closing
from . import cs
from . import degiro
from . import easyride
from . import finpension
from . import galaxus
from . import gmail
from . import google_play_mail
from . import ib
from . import ibplaywright
from . import mbank
from . import op
from . import patreon
from . import playwrightutils
from .playwrightutils import Browser
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


XDG_CONFIG_HOME = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser(
    '~/.config')


@click.group()
@click.option('--config_file',
              default=os.path.join(XDG_CONFIG_HOME, 'findata', 'fetcher.json'),
              type=click.File(mode='r'),
              help='The file containing the program\'s config ' +
              '(default: $XDG_CONFIG_HOME/findata/fetcher.json).')
@click.pass_context
def cli(ctx, config_file: typing.TextIO):
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
    """Fetches BCGE data and outputs a CSV file."""
    config = read_config_from_context(ctx)
    credentials = bcge.fetch_credentials()
    download_directory = PurePath(config['download_directory'])

    async def run():
        async with async_playwright() as pw:
            browser = await pw.firefox.launch(
                headless=False, downloads_path=download_directory)
            statement = await bcge.fetch_account_statement(
                await browser.new_page(), credentials)
            await browser.close()

        sys.stdout.buffer.write(statement)

    asyncio.run(run())


@cli.command()
def pull_bcgecc() -> None:
    """Fetches BCGE CC data and outputs a PDF."""
    with getFirefoxDriver() as driver:
        sys.stdout.buffer.write(
            bcgecc.fetch_data(bcgecc.fetch_credentials(), driver))


@cli.command()
@click.pass_context
@click.option('--headless/--no-headless',
              default=True,
              show_default=True,
              help='Run this command in a headless browser.')
@click.option('--verbose/--quiet',
              default=False,
              show_default=True,
              help='Turn on verbose mode.')
def pull_coop_supercard(ctx, headless: bool, verbose: bool) -> None:
    """Fetches Coop receipt PDFs from supercard.ch.

    This command saves the PDFs in the download directory.
    """
    config = ctx.obj['config']
    op_service_account_auth_token = extract_op_service_account_auth_token_from_config_or_fail(
        config)
    download_directory = Path(config['download_directory'])
    last_bc_path = Path(config['supercard_last_bc_file'])
    last_bc = coop_supercard.load_last_bc(last_bc_path)
    if verbose:
        print(f'Last pulled BC is {last_bc}.')
    service = FirefoxService(log_path=path.devnull)
    opts = webdriver.FirefoxOptions()
    if headless:
        opts.add_argument('-headless')
    with (webdriver.Firefox(options=opts, service=service) as driver,
          op.set_service_account_auth_token(op_service_account_auth_token)):
        creds: coop_supercard.Credentials = coop_supercard.fetch_credentials()
        for coop_receipt in coop_supercard.fetch_receipts(
                driver, creds, last_bc):
            if verbose:
                print(f'Saving a receipt with BC={coop_receipt.bc}.')
            coop_supercard.save_receipt(download_directory, last_bc_path,
                                        coop_receipt)


@cli.command()
@click.pass_context
@click.option('--amount', required=True)
@click.argument('wire_instructions_csv', type=click.File('r'))
def cs_send_wire_to_ib(ctx, amount: str,
                       wire_instructions_csv: typing.TextIO) -> None:
    """Sends a wire transfer to Interactive Brokers.

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

    creds = cs.fetch_credentials()

    async def run():
        async with async_playwright() as pw:
            browser = await pw.firefox.launch(headless=False)
            page = await browser.new_page()
            await cs.send_wire_to_ib(page, creds, wire_instructions_cs)
            await page.pause()
            await browser.close()

    asyncio.run(run())


@cli.command()
def pull_cs_account_history() -> None:
    """Fetches Charles Schwab's transaction history.

    Prints the CSV file to STDOUT.
    """
    creds = cs.fetch_credentials()

    async def run():
        async with async_playwright() as pw:
            # Doesn't work with Chrome. Can't login.
            browser = await pw.firefox.launch(headless=False)
            statement = await cs.download_brokerage_account_transaction_history(
                await browser.new_page(), creds)
            await browser.close()

        sys.stdout.buffer.write(statement)

    asyncio.run(run())


@cli.command()
def pull_cs_eac_history() -> None:
    """Fetches Charles Schwab EAC's transaction history.

    Prints the CSV file to STDOUT.
    """
    creds = cs.fetch_credentials()

    async def run():
        async with async_playwright() as pw:
            # Doesn't work with Chrome. Can't login.
            browser = await pw.firefox.launch(headless=False)
            statement = await cs.download_eac_transaction_history(
                await browser.new_page(), creds)
            await browser.close()

        sys.stdout.buffer.write(statement)

    asyncio.run(run())


@cli.command()
@click.pass_context
def pull_degiro_account(ctx) -> None:
    """Fetches Degiro's account statement into a CSV file."""
    config = read_config_from_context(ctx)
    creds = degiro.fetch_credentials()
    download_directory = PurePath(config['download_directory'])
    with getFirefoxDriver() as driver:
        pull_degiro_account_statement_helper(driver, download_directory, creds)


def pull_degiro_account_statement_helper(
        driver: webdriver.remote.webdriver.WebDriver,
        download_directory: PurePath, creds: degiro.Credentials) -> None:
    with open_and_save_on_success(download_directory / 'degiro-account.csv',
                                  'wb') as f:
        f.write(degiro.fetch_account_statement(driver, creds))


@cli.command()
@click.pass_context
def pull_degiro_portfolio(ctx) -> None:
    """Fetches Degiro's portfolio statement and outputs a CSV file."""
    config = read_config_from_context(ctx)
    creds = degiro.fetch_credentials()
    with getFirefoxDriver() as driver:
        sys.stdout.buffer.write(degiro.fetch_portfolio_statement(
            driver, creds))


@cli.command()
@click.pass_context
def pull_easyride_receipts(ctx) -> None:
    """Fetches EasyRide receipt PDFs."""
    config = ctx.obj['config']
    op_service_account_token = extract_op_service_account_auth_token_from_config_or_fail(
        config)
    with op.set_service_account_auth_token(op_service_account_token):
        gmail_creds = gmail.fetch_credentials()
    easyride.fetch_and_archive_receipts(
        gmail_creds,
        PurePath(config['download_directory']),
    )


@cli.command()
def pull_finpension() -> None:
    """Prints Finpension's portfolio total.

    It will print a line with the value like "12123.12\n"."""
    creds = finpension.fetch_credentials()

    async def run():
        async with async_playwright() as pw:
            browser = await pw.firefox.launch(headless=False)
            page = await browser.new_page()
            await finpension.login(page, creds)
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
def ib_cancel_pending_deposits() -> None:
    """Cancels all pending deposits.

    Outputs a CSV with wire instructions.

    Example use:

        ib-cancel-pending-deposits
    """
    credentials = ibplaywright.fetch_credentials()

    async def run():
        async with playwrightutils.new_page(Browser.FIREFOX,
                                            headless=False) as page:
            await ibplaywright.login(page, credentials)
            await ibplaywright.cancel_pending_deposits(page)

    asyncio.run(run())


@cli.command()
def ib_pull() -> None:
    """Pulls an Interactive Brokers' account statement.

    Outputs the statement CSV to stdout.
    """
    credentials = ibplaywright.fetch_credentials()
    downloads_path = Path('/tmp')

    async def run():
        async with playwrightutils.new_page(
                Browser.FIREFOX, headless=False,
                downloads_path=downloads_path) as page:
            await ibplaywright.login(page, credentials)
            statement = await ibplaywright.fetch_account_statement(
                page, Path('/tmp'))
            sys.stdout.buffer.write(statement)

    asyncio.run(run())


@cli.command()
@click.option('--source',
              required=True,
              type=click.Choice(['CS', 'BCGE'], case_sensitive=False))
@click.option('--amount', required=True)
def ib_set_up_incoming_deposit(source, amount) -> None:
    """Sets up an incoming deposit on Interactive Brokers.

    Outputs a CSV with wire instructions.

    Example use:

        ib-set-up-incoming-deposit --source=cs --amount=21.37
    """
    credentials = ibplaywright.fetch_credentials()
    service = FirefoxService(log_path=path.devnull)
    with getFirefoxDriver() as driver:
        driver.implicitly_wait(20)
        ib.login(driver, credentials)
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
def pull_mbank() -> None:
    """Fetches mBank's data and outputs a CSV file."""
    creds = mbank.fetch_credentials()
    with getFirefoxDriver() as driver:
        sys.stdout.buffer.write(mbank.fetch_mbank_data(driver, creds))


def pull_mbank_helper(driver: webdriver.remote.webdriver.WebDriver,
                      download_directory: PurePath,
                      creds: mbank.Credentials) -> None:
    with open_and_save_on_success(download_directory / 'mbank.csv', 'wb') as f:
        f.write(mbank.fetch_mbank_data(driver, creds))


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
    creds = revolut.fetch_credentials()
    download_directory = Path(download_directory)

    async def run():
        async with asyncio.timeout(80):
            async with async_playwright() as pw:
                browser = await pw.firefox.launch(
                    headless=False, downloads_path=download_directory)
                await revolut.download_statements(
                    await browser.new_page(), download_directory, creds,
                    config['revolut_account_numbers'])
                await browser.close()

    asyncio.run(run())


@cli.command()
@click.pass_context
def pull_revolut_mail(ctx) -> None:
    """Fetches Revolut statements shared through gmail."""
    config = ctx.obj['config']
    op_service_account_token = extract_op_service_account_auth_token_from_config_or_fail(
        config)
    with op.set_service_account_auth_token(op_service_account_token):
        gmail_credentials = gmail.fetch_credentials()
    revolut_mail.fetch_and_archive_statements(
        gmail_credentials,
        PurePath(config['download_directory']),
    )


@cli.command()
@click.pass_context
def pull_splitwise(ctx) -> None:
    """Fetches the Splitwise statement."""
    config = ctx.obj['config']
    op_service_account_auth_token = extract_op_service_account_auth_token_from_config_or_fail(
        config)
    with op.set_service_account_auth_token(op_service_account_auth_token):
        creds = splitwise.fetch_credentials()
        csv = splitwise.export_balances_to_csv(splitwise.fetch_balances(creds))
    sys.stdout.buffer.write(csv)


@cli.command()
@click.pass_context
def pull_galaxus(ctx) -> None:
    """Fetches Digitec-Galaxus receipts in text format."""
    config = ctx.obj['config']
    download_directory = PurePath(config['download_directory'])
    op_service_account_token = extract_op_service_account_auth_token_from_config_or_fail(
        config)
    with op.set_service_account_auth_token(op_service_account_token):
        gmail_creds = gmail.fetch_credentials()
    with contextlib.closing(gmail.connect(gmail_creds)) as inbox:
        for bill in galaxus.fetch_and_archive_bills(inbox):
            with open(download_directory / (bill.subject + '.galaxus'),
                      'w') as f:
                f.write(bill.payload)


@cli.command()
@click.pass_context
def pull_google_play_mail(ctx) -> None:
    """Fetches Google Play receipts in text format."""
    config = ctx.obj['config']
    download_directory = PurePath(config['download_directory'])
    op_service_account_token = extract_op_service_account_auth_token_from_config_or_fail(
        config)
    with op.set_service_account_auth_token(op_service_account_token):
        gmail_creds = gmail.fetch_credentials()
    with contextlib.closing(gmail.connect(gmail_creds)) as inbox:
        for bill in google_play_mail.fetch_and_archive_bills(inbox):
            with open(download_directory / (bill.subject + '.email'),
                      'w') as f:
                f.write(bill.payload)


@cli.command()
@click.pass_context
def pull_patreon(ctx) -> None:
    """Fetches Patreon receipts in text format."""
    config = ctx.obj['config']
    op_service_account_token = extract_op_service_account_auth_token_from_config_or_fail(
        config)
    with op.set_service_account_auth_token(op_service_account_token):
        gmail_creds = gmail.fetch_credentials()
    patreon.fetch_and_archive_receipts(
        gmail_creds,
        PurePath(config['download_directory']),
    )


@cli.command()
@click.pass_context
def pull_uber_eats(ctx) -> None:
    """Fetches Uber Eats receipts in text format."""
    config = ctx.obj['config']
    op_service_account_token = extract_op_service_account_auth_token_from_config_or_fail(
        config)
    with op.set_service_account_auth_token(op_service_account_token):
        creds = gmail.fetch_credentials()

    download_dir = PurePath(config['download_directory'])
    for (title, content) in ubereats.fetch_and_archive_bills(creds):
        with open(download_dir / (title + '.ubereats'), 'w') as f:
            f.write(content)


def extract_op_service_account_auth_token_from_config_or_fail(
        config: dict) -> str:
    token = config.get('1password_service_account_token')
    if token is None:
        raise Exception('1password_service_account_token not found in config.')
    return token


def main():
    cli(obj={})


if __name__ == '__main__':
    main()
