"""
Fetch my accounting data into a CSV file.

Usage: python -m fetcher.tool --help
"""

import json
import logging
import os
from os import path
import re
from typing import List

import click

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
      output_file The CSV that will contain recent transactions.
    """
    config_dict = json.loads(config_file.read())
    assert isinstance(config_dict, dict)

    if config_dict[LOGGING_FILE_CFG_KEY]:
        logging.basicConfig(filename=config_dict[LOGGING_FILE_CFG_KEY],
                            level=logging.INFO)

    # cfg = mbank.general_config_to_mbank_config(config_dict)
    # trs = mbank.pull_mbank_data(cfg)


if __name__ == '__main__':
    cli()
