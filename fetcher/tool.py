# -*- coding: utf-8 -*-
"""
Fetch my accounting data into a CSV file.

Usage: python -m fetcher.tool --help
"""

import functools
import json
import logging
from pathlib import PurePath

from selenium import webdriver  # type: ignore
import click

from . import bcge
from . import bcgecc
from . import coop
from . import cs
from . import degiro
from . import ib
from . import gmail
from . import mbank

LOGGING_FILE_CFG_KEY = 'logging_file'


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


def wrap_puller(fun):
    @cli.command()
    @click.argument('output_file', type=click.File(mode='wb', lazy=True))
    @click.pass_context
    @functools.wraps(fun)
    def pull_xxx(ctx, output_file):
        try:
            raw_data = fun(read_config_from_context(ctx))
        except Exception:
            logging.exception("Could not fetch data.")
        else:
            output_file.write(raw_data)

    return pull_xxx


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
    with open(download_directory / 'bcge.csv', 'wb') as f:
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
    with open(download_directory / 'bcgecc.csv', 'wb') as f:
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
    with open(download_directory / 'cs.csv', 'wb') as f:
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
    with open(download_directory / 'degiro.csv', 'wb') as f:
        f.write(
            degiro.fetch_account_statement(driver,
                                           extract_degiro_credentials(config)))


@wrap_puller
def pull_degiro_portfolio(config: dict) -> bytes:
    """Fetches Degiro's portfolio statement into a CSV file."""
    return degiro.fetch_portfolio_statement(extract_degiro_credentials(config))


@cli.command()
@click.pass_context
def pull_ib(ctx) -> None:
    """Fetches Interactive Brokers into a CSV file."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config['download_directory'])
    with webdriver.Firefox() as driver:
        pull_ib_helper(driver, download_directory, config)


def pull_ib_helper(driver: webdriver.remote.webdriver.WebDriver,
                   download_directory: PurePath, config: dict) -> None:
    with open(download_directory / 'ib.csv', 'wb') as f:
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
    with open(download_directory / 'mbank.csv', 'wb') as f:
        f.write(
            mbank.fetch_mbank_data(driver, extract_mbank_credentials(config)))


@cli.command()
@click.pass_context
def pull_all(ctx) -> None:
    """Fetches data from all implemented sources."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config['download_directory'])
    coop.fetch_and_archive_receipts(
        extract_gmail_credentials(config),
        download_directory,
    )
    with webdriver.Firefox() as driver:
        pull_bcge_helper(driver, download_directory, config)
        pull_bcgecc_helper(driver, download_directory, config)
        pull_cs_account_history_helper(driver, download_directory, config)
        pull_degiro_account_statement_helper(driver, download_directory,
                                             config)
        pull_ib_helper(driver, download_directory, config)
        pull_mbank_helper(driver, download_directory, config)


def extract_bcge_credentials(config: dict) -> bcge.Credentials:
    return bcge.Credentials(id=config['bcge_id'], pwd=config['bcge_pwd'])


def extract_bcgecc_credentials(config: dict) -> bcgecc.Credentials:
    return bcgecc.Credentials(id=config['bcgecc_id'], pwd=config['bcgecc_pwd'])


def extract_cs_credentials(config: dict) -> cs.Credentials:
    return cs.Credentials(id=config['cs_id'], pwd=config['cs_pwd'])


def extract_degiro_credentials(config: dict) -> degiro.Credentials:
    return degiro.Credentials(id=config['degiro_id'], pwd=config['degiro_pwd'])


def extract_ib_credentials(config: dict) -> ib.Credentials:
    return ib.Credentials(id=config['ib_id'], pwd=config['ib_pwd'])


def extract_gmail_credentials(config: dict) -> gmail.Credentials:
    return gmail.Credentials(id=config['gmail_id'], pwd=config['gmail_pwd'])


def extract_mbank_credentials(config: dict) -> mbank.Credentials:
    return mbank.Credentials(id=config['mbank_id'], pwd=config['mbank_pwd'])


if __name__ == '__main__':
    cli(obj={})
