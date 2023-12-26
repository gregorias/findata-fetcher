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
from playwright.async_api import async_playwright

pw = async_playwright
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
from . import google_play_mail
from . import ib
from . import mbank
from . import op
from . import patreon
from . import playwrightutils
from .playwrightutils import Browser
from . import revolut
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
FETCHER_CONFIG_DEFAULT: str = os.path.join(XDG_CONFIG_HOME, 'findata',
                                           'fetcher.json')


@click.group()
@click.option('--config_file',
              default=FETCHER_CONFIG_DEFAULT,
              type=click.File(mode='r'),
              help='The file containing the program\'s config ' +
              '(default: $XDG_CONFIG_HOME/findata/fetcher.json).')
@click.option('--logtostderr/--no-logtostderr',
              default=False,
              help='Whether to log to STDERR.')
@click.pass_context
def cli(ctx, config_file: typing.TextIO, logtostderr: bool):
    config = json.load(config_file)
    assert isinstance(config, dict)

    ctx.obj['config'] = config

    if config[LOGGING_FILE_CFG_KEY]:
        logging.basicConfig(filename=config[LOGGING_FILE_CFG_KEY],
                            level=logging.DEBUG)
    stderr = logging.StreamHandler()
    stderr.setLevel(logging.INFO if logtostderr else logging.WARNING)
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
        async with playwrightutils.new_page(
                Browser.CHROMIUM, downloads_path=download_directory) as p:
            statement = await bcge.fetch_account_statement(p, credentials)

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
def coop_supercard_pull(ctx, headless: bool, verbose: bool) -> None:
    """Fetches Coop receipt PDFs from supercard.ch.

    This command saves the PDFs in the download directory.

    supercard.ch occasionally asks for a captcha. When this happens, human
    intervention is required.
    """
    config = ctx.obj['config']
    op_service_account_auth_token = extract_op_service_account_auth_token_from_config_or_fail(
        config)
    download_directory = Path(config['download_directory'])
    last_bc_path = Path(config['supercard_last_bc_file'])
    last_bc = coop_supercard.load_last_bc(last_bc_path)
    if verbose:
        print(f'Last pulled BC is {last_bc}.')
    with op.set_service_account_auth_token(op_service_account_auth_token):
        creds: coop_supercard.Credentials = coop_supercard.fetch_credentials()

    async def run():
        async with async_playwright() as pw:
            browser = await pw.firefox.launch(headless=headless)
            context = await browser.new_context(no_viewport=not headless)
            page = await context.new_page()
            reverse_chronological_receipt_urls = await coop_supercard.fetch_receipt_urls(
                page, creds)
            # Wait 5 seconds to make sure that all background scripts have done their work.
            await asyncio.sleep(5)
            cookies = playwrightutils.playwright_cookie_jar_to_requests_cookies(
                await context.cookies())
            chronological_unprocessed_receipt_urls = coop_supercard.get_chronological_unprocessed_urls(
                reverse_chronological_receipt_urls, last_bc)
            for coop_receipt in coop_supercard.fetch_receipts(
                    chronological_unprocessed_receipt_urls,
                    lambda url: coop_supercard.fetch_receipt(url, cookies)):
                if verbose:
                    print(f'Saving a receipt with BC={coop_receipt.bc}.')
                coop_supercard.save_receipt(download_directory,
                                            last_bc_path,
                                            receipt=coop_receipt)
            await page.close()
            await context.close()
            await browser.close()

    asyncio.run(run())


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

    raise NotImplementedError()
    # wire_instructions_ib = ib.wire_instructions(
    #    decode_ib_wire_instructions(wire_instructions_csv))
    #  wire_instructions_cs = cs.WireInstructions(
    #      amount=amount,
    #      bank_routing_number=wire_instructions_ib.aba_routing_number,
    #      beneficiary_account_number=wire_instructions_ib.bank_account_number,
    #      for_further_credit=cs.ForFurtherCreditInstructions(
    #          account_number=ffc_config['account_number'],
    #          address=ffc_config['address'],
    #          city_and_state=ffc_config['city_and_state'],
    #          country=ffc_config['country'],
    #          name=ffc_config['name'],
    #          notes=ffc_config['notes'],
    #      ),
    #  )

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
        # Doesn't work with Chrome. Can't login.
        # Non-headless mode, because it requires manual OTP input.
        async with playwrightutils.new_page(Browser.FIREFOX,
                                            headless=False) as page:
            return await cs.download_eac_transaction_history(page, creds)

    statement = asyncio.run(run())
    sys.stdout.buffer.write(statement)


@cli.command()
@click.pass_context
def degiro_account_pull(ctx) -> None:
    """Fetches Degiro's account statement and outputs a CSV file."""
    asyncio.run(degiro_pull(ctx, degiro.StatementType.ACCOUNT))


@cli.command()
@click.pass_context
def degiro_portfolio_pull(ctx) -> None:
    """Fetches Degiro's portfolio statement and outputs a CSV file."""
    asyncio.run(degiro_pull(ctx, degiro.StatementType.PORTFOLIO))


async def degiro_pull(ctx, statement_type: degiro.StatementType) -> None:
    config = read_config_from_context(ctx)
    creds = degiro.fetch_credentials()
    async with playwrightutils.new_page(Browser.FIREFOX,
                                        headless=False) as page:
        await degiro.login(page, creds)
        statement = await degiro.fetch_statement(page, statement_type)

    sys.stdout.buffer.write(statement)


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
    credentials = ib.fetch_credentials()

    async def run():
        async with playwrightutils.new_page(Browser.FIREFOX,
                                            headless=False) as page:
            await ib.login(page, credentials)
            await ib.cancel_pending_deposits(page)

    asyncio.run(run())


@cli.command()
def ib_pull() -> None:
    """Pulls an Interactive Brokers' account statement.

    Outputs the statement CSV to stdout.
    """
    credentials = ib.fetch_credentials()
    downloads_path = Path('/tmp')

    async def run():
        async with playwrightutils.new_page(
                Browser.FIREFOX, headless=False,
                downloads_path=downloads_path) as page:
            await ib.login(page, credentials)
            statement = await ib.fetch_account_statement(page, Path('/tmp'))
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
    ib_source: ib.DepositSource = (ib.DepositSource.BCGE if source == 'BCGE'
                                   else ib.DepositSource.CHARLES_SCHWAB)
    credentials: ib.Credentials = ib.fetch_credentials()

    async def run() -> ib.SourceBankDepositInformation:
        async with playwrightutils.new_page(Browser.FIREFOX,
                                            headless=False) as page:
            await ib.login(page, credentials)
            instructions: ib.SourceBankDepositInformation = (await ib.deposit(
                page, ib_source, decimal.Decimal(amount)))
            return instructions

    instructions = asyncio.run(run())

    writer = csv.DictWriter(sys.stdout,
                            fieldnames=["key", "value"],
                            delimiter=',')
    writer.writeheader()
    writer.writerow({
        'key': 'transfer_to',
        'value': instructions.transfer_to,
    })
    writer.writerow({
        'key': 'iban',
        'value': instructions.iban,
    })
    writer.writerow({
        'key': 'beneficiary_bank',
        'value': instructions.beneficiary_bank,
    })
    writer.writerow({
        'key': 'for_further_credit',
        'value': instructions.for_further_credit,
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
def revolut_pull(ctx, download_directory) -> None:
    """Fetches Revolut data into CSV files."""
    config = read_config_from_context(ctx)
    download_directory = Path(download_directory)

    async def run():
        async with playwrightutils.new_page(
                browser_type=Browser.FIREFOX,
                downloads_path=download_directory) as p:
            await revolut.download_statements(
                p, download_directory, config['revolut_account_numbers'])

    asyncio.run(run())


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
