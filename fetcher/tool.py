# -*- coding: utf-8 -*-
"""
Fetch my accounting data into a CSV file.

Usage: python -m fetcher.tool --help
"""

from contextlib import contextmanager
import functools
import json
import logging
from pathlib import PurePath
import tempfile
import shutil

from selenium import webdriver  # type: ignore
from seleniumwire import webdriver as webdriverwire  # type: ignore
import click  # type: ignore

from . import bcge
from . import bcgecc
from . import coop
from . import cs
from . import degiro
from . import easyride
from . import finpension
from . import galaxus
from . import ib
from . import gmail
from . import mbank
from . import patreon
from . import revolut
from . import revolut_mail
from . import splitwise
from . import ubereats

LOGGING_FILE_CFG_KEY = 'logging_file'


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
    with webdriver.Firefox() as driver:
        return pull_bcge_helper(driver, download_directory, config)


def pull_bcge_helper(driver: webdriver.remote.webdriver.WebDriver,
                     download_directory: PurePath, config: dict) -> None:
    with open_and_save_on_success(download_directory / 'bcge.csv', 'wb') as f:
        f.write(bcge.fetch_bcge_data(driver, extract_bcge_credentials(config)))


@cli.command()
@click.pass_context
def pull_bcgecc(ctx) -> None:
    """Fetches BCGE CC data into a CSV file."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config['download_directory'])
    with webdriver.Firefox() as driver:
        return pull_bcgecc_helper(driver, download_directory, config)


def pull_bcgecc_helper(driver: webdriver.remote.webdriver.WebDriver,
                       download_directory: PurePath, config: dict) -> None:
    with open_and_save_on_success(download_directory / 'bcgecc.pdf',
                                  'wb') as f:
        f.write(bcgecc.fetch_data(extract_bcgecc_credentials(config), driver))


@cli.command()
@click.pass_context
def pull_coop_receipts(ctx) -> None:
    """Fetches Coop receipt PDFs."""
    config = ctx.obj['config']
    coop.fetch_and_archive_receipts(
        extract_gmail_credentials(config),
        PurePath(config['download_directory']),
    )


@cli.command()
@click.pass_context
def pull_cs_account_history(ctx) -> None:
    """Fetches Charles Schwab account history into a CSV file."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config['download_directory'])
    with webdriver.Firefox() as driver:
        pull_cs_account_history_helper(driver, download_directory, config)


def pull_cs_account_history_helper(
        driver: webdriver.remote.webdriver.WebDriver,
        download_directory: PurePath, config: dict) -> None:
    with open_and_save_on_success(download_directory / 'cs.csv', 'wb') as f:
        f.write(
            cs.fetch_account_history(driver, extract_cs_credentials(config)))


@cli.command()
@click.pass_context
def pull_degiro_account(ctx) -> None:
    """Fetches Degiro's account statement into a CSV file."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config['download_directory'])
    with webdriver.Firefox() as driver:
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
    """Fetches Degiro's portfolio statement into a CSV file."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config['download_directory'])
    with webdriver.Firefox() as driver:
        pull_degiro_portfolio_helper(driver, download_directory, config)


def pull_degiro_portfolio_helper(driver: webdriver.remote.webdriver.WebDriver,
                                 download_directory: PurePath,
                                 config: dict) -> None:
    with open_and_save_on_success(download_directory / 'degiro-portfolio.csv',
                                  'wb') as f:
        f.write(
            degiro.fetch_portfolio_statement(
                driver, extract_degiro_credentials(config)))


@cli.command()
@click.pass_context
def pull_degiro(ctx) -> None:
    """Fetches Degiro's account and portfolio statements into CSV files."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config['download_directory'])
    with webdriver.Firefox() as driver:
        pull_degiro_helper(driver, download_directory, config)


def pull_degiro_helper(driver: webdriver.remote.webdriver.WebDriver,
                       download_directory: PurePath, config: dict) -> None:
    with open_and_save_on_success(download_directory / 'degiro-portfolio.csv',
                                  'wb') as p:
        with open_and_save_on_success(
                download_directory / 'degiro-account.csv', 'wb') as a:
            (account_stmt, portfolio_stmt) = degiro.fetch_all(
                driver, extract_degiro_credentials(config))
            a.write(account_stmt)
            p.write(portfolio_stmt)


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
    """Fetches Finpension transactions into a CSV file."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config['download_directory'])
    with webdriver.Firefox() as driver:
        pull_finpension_helper(driver, download_directory, config)


def pull_finpension_helper(driver: webdriver.remote.webdriver.WebDriver,
                           download_directory: PurePath, config: dict) -> None:
    with open_and_save_on_success(download_directory / 'finpension.csv',
                                  'wb') as f:
        f.write(
            finpension.fetch_data(extract_finpension_credentials(config),
                                  extract_gmail_credentials(config), driver))


@cli.command()
@click.pass_context
def pull_ib(ctx) -> None:
    """Fetches Interactive Brokers into a CSV file."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config['download_directory'])
    with webdriverwire.Firefox() as driver:
        pull_ib_helper(driver, download_directory, config)


def pull_ib_helper(driver: webdriver.remote.webdriver.WebDriver,
                   download_directory: PurePath, config: dict) -> None:
    with open_and_save_on_success(download_directory / 'ib.csv', 'wb') as f:
        f.write(ib.fetch_data(driver, extract_ib_credentials(config)))


@cli.command()
@click.pass_context
def pull_mbank(ctx) -> None:
    """Fetches Mbank data into a CSV file."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config['download_directory'])
    with webdriver.Firefox() as driver:
        pull_mbank_helper(driver, download_directory, config)


def pull_mbank_helper(driver: webdriver.remote.webdriver.WebDriver,
                      download_directory: PurePath, config: dict) -> None:
    with open_and_save_on_success(download_directory / 'mbank.csv', 'wb') as f:
        f.write(
            mbank.fetch_mbank_data(driver, extract_mbank_credentials(config)))


@cli.command()
@click.pass_context
def pull_revolut(ctx) -> None:
    """Fetches Revolut data into CSV files."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config['download_directory'])
    with webdriver.Firefox() as driver:
        pull_revolut_helper(driver, download_directory, config)


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
    bs = splitwise.fetch_balances(extract_splitwise_credentials(config))
    csv = splitwise.export_balances(bs)
    download_directory = PurePath(config['download_directory'])
    with open(download_directory / 'splitwise.csv', 'wb') as f:
        f.write(csv)


def pull_revolut_helper(driver: webdriver.remote.webdriver.WebDriver,
                        download_directory: PurePath, config: dict) -> None:
    creds = extract_revolut_credentials(config)
    raise Exception("pull-revolut is not yet implemented.")


@cli.command()
@click.pass_context
def pull_galaxus(ctx) -> None:
    """Fetches Digitec-Galaxus receipts in text format."""
    config = ctx.obj['config']
    for content in galaxus.fetch_and_archive_bills(
            extract_gmail_credentials(config)):
        print(content)


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


@cli.command()
@click.pass_context
def pull_all(ctx) -> None:
    """Fetches data from all implemented sources."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config['download_directory'])
    gmail_creds = extract_gmail_credentials(config)
    coop.fetch_and_archive_receipts(
        gmail_creds,
        download_directory,
    )
    easyride.fetch_and_archive_receipts(
        gmail_creds,
        download_directory,
    )
    with webdriverwire.Firefox() as driver:
        pull_ib_helper(driver, download_directory, config)
    with webdriver.Firefox() as driver:
        pull_bcge_helper(driver, download_directory, config)
        pull_bcgecc_helper(driver, download_directory, config)
        pull_cs_account_history_helper(driver, download_directory, config)
        pull_degiro_helper(driver, download_directory, config)
        pull_mbank_helper(driver, download_directory, config)
        pull_revolut_helper(driver, download_directory, config)


def extract_bcge_credentials(config: dict) -> bcge.Credentials:
    return bcge.Credentials(id=config['bcge_id'], pwd=config['bcge_pwd'])


def extract_bcgecc_credentials(config: dict) -> bcgecc.Credentials:
    return bcgecc.Credentials(id=config['bcgecc_id'], pwd=config['bcgecc_pwd'])


def extract_cs_credentials(config: dict) -> cs.Credentials:
    return cs.Credentials(id=config['cs_id'], pwd=config['cs_pwd'])


def extract_degiro_credentials(config: dict) -> degiro.Credentials:
    return degiro.Credentials(id=config['degiro_id'], pwd=config['degiro_pwd'])


def extract_finpension_credentials(config: dict) -> finpension.Credentials:
    return finpension.Credentials(id=config['finpension_id'],
                                  pwd=config['finpension_pwd'])


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


def extract_splitwise_credentials(config: dict) -> splitwise.Credentials:
    return splitwise.Credentials(
        consumer_key=config['splitwise_consumer_key'],
        consumer_secret=config['splitwise_consumer_secret'],
        api_key=config['splitwise_api_key'])


if __name__ == '__main__':
    cli(obj={})
