"""
Fetch my accounting data into a CSV file.

Usage: python -m fetcher.tool --help
"""

import asyncio
import contextlib
import csv
import decimal
import json
import logging
import os
import shutil
import sys
import tempfile
import typing
from contextlib import contextmanager
from os import path
from pathlib import Path, PurePath

import click
from playwright.async_api import async_playwright
from selenium import webdriver  # type: ignore
from selenium.webdriver.firefox.service import Service as FirefoxService  # type: ignore

from . import (
    bcge,
    bcgecc,
    coop_supercard,
    degiro,
    easyride,
    finpension,
    galaxus,
    gmail,
    google_play_mail,
    ib,
    mbank,
    op,
    patreon,
    playwrightutils,
    revolut,
    splitwise,
    ubereats,
)
from .playwrightutils import Browser

pw = async_playwright

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
    download_directory = PurePath(config['download_directory'])

    async def run():
        credentials = await bcge.fetch_credentials(await connect_op(config))
        async with playwrightutils.new_page(
                Browser.CHROMIUM, downloads_path=download_directory) as p:
            statement = await bcge.fetch_account_statement(p, credentials)
        sys.stdout.buffer.write(statement)

    asyncio.run(run())


@cli.command()
@click.pass_context
def pull_bcgecc(ctx) -> None:
    """Fetches BCGE CC data and outputs a PDF."""
    config = read_config_from_context(ctx)

    async def run():
        with getFirefoxDriver() as driver:
            sys.stdout.buffer.write(
                bcgecc.fetch_data(
                    await bcgecc.fetch_credentials(await connect_op(config)),
                    driver))

    asyncio.run(run())


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

    This command:

    * Saves the PDFs in the download directory as "Coop BC.pdf".\n
    * Writes the last receipts’ BC (an identifier) to the last BC file.

    supercard.ch occasionally asks for a captcha. When this happens, human
    intervention is required.
    """
    config = ctx.obj['config']
    download_directory = Path(config['download_directory'])
    last_bc_path = Path(config['supercard_last_bc_file'])

    def print_if_verbose(msg):
        return print(msg) if verbose else lambda _: None

    async def run() -> None:
        creds: coop_supercard.Credentials = (await
                                             coop_supercard.fetch_credentials(
                                                 await connect_op(config)))
        # Use Chromium. In July 2024, Firefox stopped working: the login
        # page was loading indefinitely.
        async with playwrightutils.new_stack(
            browser_type=Browser.CHROMIUM,
            headless=headless) as (pw, browser, browser_context, page):

            await coop_supercard.fetch_and_save_receipts(
                last_bc_path, download_directory, creds, page, browser_context,
                print_if_verbose)

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
    raise NotImplementedError()


@cli.command()
def pull_cs_account_history() -> None:
    """Fetches Charles Schwab's transaction history.

    Prints the CSV file to STDOUT.
    """
    # Stopped working in July 2024, the login page was blocking me.
    raise NotImplementedError()


@cli.command()
def pull_cs_eac_history() -> None:
    """Fetches Charles Schwab EAC's transaction history.

    Prints the CSV file to STDOUT.
    """
    # Stopped working in July 2024, the login page was blocking me.
    raise NotImplementedError()


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
    op_client = await connect_op(ctx.obj['config'])
    creds = await degiro.fetch_credentials(op_client)
    async with playwrightutils.new_page(Browser.FIREFOX,
                                        headless=False) as page:
        await degiro.login(page, creds, op_client)
        statement = await degiro.fetch_statement(page, statement_type)

    sys.stdout.buffer.write(statement)


@cli.command()
@click.pass_context
def pull_easyride_receipts(ctx) -> None:
    """Fetches EasyRide receipt PDFs."""
    config = ctx.obj['config']

    async def run():
        easyride.fetch_and_archive_receipts(
            await gmail.fetch_credentials(await connect_op(config)),
            PurePath(config['download_directory']),
        )

    asyncio.run(run())


@cli.command()
@click.pass_context
def pull_finpension(ctx) -> None:
    """Prints Finpension’s portfolio total.

    It will print a line with the value like "12123.12\n"."""
    config = ctx.obj['config']

    async def run():
        async with async_playwright() as pw:
            browser = await pw.firefox.launch(headless=False)
            page = await browser.new_page()
            await finpension.login(
                page, await finpension.fetch_credentials(await
                                                         connect_op(config)))
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
def ib_cancel_pending_deposits(ctx) -> None:
    """Cancels all pending deposits.

    Outputs a CSV with wire instructions.

    Example use:

        ib-cancel-pending-deposits
    """
    config = ctx.obj['config']

    async def run():
        credentials = await ib.fetch_credentials(await connect_op(config))
        async with playwrightutils.new_page(Browser.FIREFOX,
                                            headless=False) as page:
            await ib.login(page, credentials)
            await ib.cancel_pending_deposits(page)

    asyncio.run(run())


@cli.command()
@click.pass_context
def ib_activity_pull(ctx) -> None:
    """Pulls Interactive Brokers' activity statement.

    Outputs the statement CSV to stdout.
    """
    config = ctx.obj['config']
    downloads_path = Path('/tmp')

    async def run():
        credentials = await ib.fetch_credentials(await connect_op(config))
        async with playwrightutils.new_page(
                Browser.FIREFOX, headless=False,
                downloads_path=downloads_path) as page:
            await ib.login(page, credentials)
            statement = await ib.fetch_statement(page,
                                                 ib.StatementType.ACTIVITY,
                                                 Path('/tmp'))
            sys.stdout.buffer.write(statement)

    asyncio.run(run())


@cli.command()
@click.option('--source',
              required=True,
              type=click.Choice(['CS', 'BCGE'], case_sensitive=False))
@click.option('--amount', required=True)
@click.pass_context
def ib_set_up_incoming_deposit(ctx, source, amount) -> None:
    """Sets up an incoming deposit on Interactive Brokers.

    Outputs a CSV with wire instructions.

    Example use:

        ib-set-up-incoming-deposit --source=cs --amount=21.37
    """
    config = ctx.obj['config']
    ib_source: ib.DepositSource = (ib.DepositSource.BCGE if source == 'BCGE'
                                   else ib.DepositSource.CHARLES_SCHWAB)

    async def run() -> ib.SourceBankDepositInformation:
        credentials: ib.Credentials = await ib.fetch_credentials(
            await connect_op(config))
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
@click.pass_context
def pull_mbank(ctx) -> None:
    """Fetches mBank's data and outputs a CSV file."""
    config = read_config_from_context(ctx)

    async def run():
        creds = await mbank.fetch_credentials(await connect_op(config))
        with getFirefoxDriver() as driver:
            sys.stdout.buffer.write(mbank.fetch_mbank_data(driver, creds))

    asyncio.run(run())


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

    async def run():
        creds = await splitwise.fetch_credentials(await connect_op(config))
        csv = splitwise.export_balances_to_csv(splitwise.fetch_balances(creds))
        sys.stdout.buffer.write(csv)

    asyncio.run(run())


@cli.command()
@click.pass_context
def pull_galaxus(ctx) -> None:
    """Fetches Digitec-Galaxus receipts in text format."""
    config = ctx.obj['config']
    download_directory = PurePath(config['download_directory'])

    async def run():
        with contextlib.closing(
                gmail.connect(await
                              gmail.fetch_credentials(await connect_op(config)
                                                      ))) as inbox:
            for bill in galaxus.fetch_and_archive_bills(inbox):
                with open(download_directory / (bill.subject + '.galaxus'),
                          'w') as f:
                    f.write(bill.payload)

    asyncio.run(run())


@cli.command()
@click.pass_context
def pull_google_play_mail(ctx) -> None:
    """Fetches Google Play receipts in text format."""
    config = ctx.obj['config']
    download_directory = PurePath(config['download_directory'])

    async def run():
        with contextlib.closing(
                gmail.connect(await
                              gmail.fetch_credentials(await connect_op(config)
                                                      ))) as inbox:
            for bill in google_play_mail.fetch_and_archive_bills(inbox):
                with open(download_directory / (bill.subject + '.email'),
                          'w') as f:
                    f.write(bill.payload)

    asyncio.run(run())


@cli.command()
@click.pass_context
def pull_patreon(ctx) -> None:
    """Fetches Patreon receipts in text format."""
    config = ctx.obj['config']

    async def run():
        patreon.fetch_and_archive_receipts(
            await gmail.fetch_credentials(await connect_op(config)),
            PurePath(config['download_directory']),
        )

    asyncio.run(run())


@cli.command()
@click.pass_context
def pull_uber_eats(ctx) -> None:
    """Fetches Uber Eats receipts in text format."""
    config = ctx.obj['config']
    download_dir = PurePath(config['download_directory'])

    async def run():
        for (title, content) in ubereats.fetch_and_archive_bills(
                await gmail.fetch_credentials(await connect_op(config))):
            with open(download_dir / (title + '.ubereats'), 'w') as f:
                f.write(content)

    asyncio.run(run())


def extract_op_service_account_auth_token_from_config_or_fail(
        config: dict) -> str:
    token = config.get('1password_service_account_token')
    if token is None:
        raise Exception('1password_service_account_token not found in config.')
    return token


async def connect_op(config: dict) -> op.OpSdkClient:
    op_service_account_auth_token = extract_op_service_account_auth_token_from_config_or_fail(
        config)
    return await op.OpSdkClient.connect(
        service_account_auth_token=op_service_account_auth_token)


def main():
    cli(obj={})


if __name__ == '__main__':
    main()
