"""
Fetch my accounting data into a CSV file.

Usage: python -m fetcher.tool --help
"""

import json
import logging
from os import path
from typing import List
import sys

import click

from . import mbank

LOGGING_FILE_CFG_KEY = 'logging_file'


@click.group()
def cli():
    pass


@cli.command()
@click.option('--config_file',
              default='config.json',
              type=click.File(mode='r'),
              help='The file containing the program\'s config')
@click.argument('output_file', type=click.File(mode='w', lazy=True))
def pull_mbank(config_file, output_file):
    """Fetch my mbank data into a ledger-like file.

    Arguments:
      output_file The JSON file that will contain recent transactions
    """
    config = json.loads(config_file.read())
    assert isinstance(config, dict)

    if config[LOGGING_FILE_CFG_KEY]:
        logging.basicConfig(filename=config[LOGGING_FILE_CFG_KEY],
                            level=logging.DEBUG)

    try:
        transactions = mbank.fetch_raw_mbank_data(
            extract_mbank_credentials(config))
    except Exception:
        logging.exception("Could not fetch Mbank data.")
        sys.exit(1)

    with open(output_file, 'w'):
        json.dump(transactions, output_file)


def extract_mbank_credentials(config: dict) -> mbank.Credentials:
    return mbank.Credentials(id=config['mbank_id'], pwd=config['mbank_pwd'])


if __name__ == '__main__':
    cli()
