"""
Fetch my accounting data into a CSV file.

Usage: python -m fetcher.tool --help
"""

import functools
import json
import logging

import click

from . import bcge
from . import bcgecc
from . import degiro
from . import ib
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


def wrap_puller(fun):
    @cli.command()
    @click.argument('output_file', type=click.File(mode='wb', lazy=True))
    @click.pass_context
    @functools.wraps(fun)
    def pull_xxx(ctx, output_file):
        try:
            raw_data = fun(ctx.obj['config'])
        except Exception:
            logging.exception("Could not fetch data.")
        else:
            output_file.write(raw_data)

    return pull_xxx


@wrap_puller
def pull_bcge(config: dict) -> bytes:
    """Fetches BCGE data into a CSV file."""
    return bcge.fetch_bcge_data(extract_bcge_credentials(config))


@wrap_puller
def pull_bcgecc(config: dict) -> bytes:
    """Fetches BCGE CC data into a CSV file."""
    return bcgecc.fetch_data(extract_bcgecc_credentials(config))


@wrap_puller
def pull_degiro_account(config: dict) -> bytes:
    """Fetches Degiro's account statement into a CSV file."""
    return degiro.fetch_account_statement(extract_degiro_credentials(config))


@wrap_puller
def pull_degiro_portfolio(config: dict) -> bytes:
    """Fetches Degiro's portfolio statement into a CSV file."""
    return degiro.fetch_portfolio_statement(extract_degiro_credentials(config))


@wrap_puller
def pull_ib(config: dict) -> bytes:
    """Fetches Interactive Brokers into a CSV file."""
    return ib.fetch_data(extract_ib_credentials(config))


@wrap_puller
def pull_mbank(config: dict) -> bytes:
    """Fetches Mbank data into a CSV file."""
    return mbank.fetch_mbank_data(extract_mbank_credentials(config))


def extract_bcge_credentials(config: dict) -> bcge.Credentials:
    return bcge.Credentials(id=config['bcge_id'], pwd=config['bcge_pwd'])


def extract_bcgecc_credentials(config: dict) -> bcgecc.Credentials:
    return bcgecc.Credentials(id=config['bcgecc_id'], pwd=config['bcgecc_pwd'])


def extract_degiro_credentials(config: dict) -> degiro.Credentials:
    return degiro.Credentials(id=config['degiro_id'], pwd=config['degiro_pwd'])


def extract_ib_credentials(config: dict) -> ib.Credentials:
    return ib.Credentials(id=config['ib_id'], pwd=config['ib_pwd'])


def extract_mbank_credentials(config: dict) -> mbank.Credentials:
    return mbank.Credentials(id=config['mbank_id'], pwd=config['mbank_pwd'])


if __name__ == '__main__':
    cli(obj={})
