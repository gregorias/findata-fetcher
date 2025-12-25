"""
Fetch my accounting data from various sources.

Usage: python -m fetcher.tool --help
"""

import asyncio
import contextlib
import csv
import decimal
import json
import logging
import os
import sys
import typing
from pathlib import Path, PurePath

import click
from playwright.async_api import async_playwright

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

LOGGING_FILE_CFG_KEY = "logging_file"

XDG_CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
FETCHER_CONFIG_DEFAULT: str = os.path.join(XDG_CONFIG_HOME, "findata", "fetcher.json")


@click.group()
@click.option(
    "--config_file",
    default=FETCHER_CONFIG_DEFAULT,
    type=click.File(mode="r"),
    help="The file containing the program's config "
    + "(default: $XDG_CONFIG_HOME/findata/fetcher.json).",
)
@click.option(
    "--logtostderr/--no-logtostderr", default=False, help="Whether to log to STDERR."
)
@click.pass_context
def cli(ctx, config_file: typing.TextIO, logtostderr: bool):
    config = json.load(config_file)
    assert isinstance(config, dict)

    ctx.obj["config"] = config

    if config[LOGGING_FILE_CFG_KEY]:
        logging.basicConfig(filename=config[LOGGING_FILE_CFG_KEY], level=logging.DEBUG)
    stderr = logging.StreamHandler()
    stderr.setLevel(logging.INFO if logtostderr else logging.WARNING)
    logging.getLogger("").addHandler(stderr)


def read_config_from_context(ctx):
    return ctx.obj["config"]


@cli.command()
@click.pass_context
def pull_bcge(ctx) -> None:
    """Fetches BCGE data and outputs a CSV file."""
    config = read_config_from_context(ctx)
    download_directory = PurePath(config["download_directory"])

    async def run():
        credentials = await bcge.fetch_credentials(await connect_op())
        async with playwrightutils.new_page(
            Browser.CHROMIUM, downloads_path=download_directory
        ) as p:
            statement = await bcge.fetch_account_statement(p, credentials)
        sys.stdout.buffer.write(statement)

    asyncio.run(run())


@cli.command()
def pull_bcgecc() -> None:
    """Fetches BCGE CC data and outputs a PDF."""

    async def run():
        creds = await bcgecc.fetch_credentials(await connect_op())
        async with playwrightutils.new_page(Browser.FIREFOX) as p:
            statement = await bcgecc.login_and_download_latest_statement(p, creds)
        sys.stdout.buffer.write(statement)

    asyncio.run(run())


@cli.command()
def coop_supercard_pull() -> None:
    """Fetches Coop receipt PDFs from coop.ch.

    This command saves `receipt *.pdf` files to the download directory.

    This command just opens the Coop page in the default browser.
    Coop starter blocking Playwright (and presumably other automation) in late
    2024.
    """
    coop_supercard.fetch_receipts_manually()


@cli.command()
@click.pass_context
@click.option("--amount", required=True)
@click.argument("wire_instructions_csv", type=click.File("r"))
def cs_send_wire_to_ib(ctx, amount: str, wire_instructions_csv: typing.TextIO) -> None:
    """Sends a wire transfer to Interactive Brokers.

    Example use:

        cs-send-wire-to-ib --amount=21.37 WIRE_INSTRUCTIONS_CSV
    """
    raise NotImplementedError()


@cli.command()
def degiro_account_pull() -> None:
    """Fetches Degiro's account statement and outputs a CSV file."""
    asyncio.run(degiro_pull(degiro.StatementType.ACCOUNT))


@cli.command()
def degiro_portfolio_pull() -> None:
    """Fetches Degiro's portfolio statement and outputs a CSV file."""
    asyncio.run(degiro_pull(degiro.StatementType.PORTFOLIO))


async def degiro_pull(statement_type: degiro.StatementType) -> None:
    op_client = await connect_op()
    creds = await degiro.fetch_credentials(op_client)
    async with playwrightutils.new_page(Browser.FIREFOX, headless=False) as page:
        await degiro.login(page, creds, op_client)
        statement = await degiro.fetch_statement(page, statement_type)

    sys.stdout.buffer.write(statement)


@cli.command()
@click.pass_context
def pull_easyride_receipts(ctx) -> None:
    """Fetches EasyRide receipt PDFs."""
    config = ctx.obj["config"]

    async def run():
        easyride.fetch_and_archive_receipts(
            await gmail.fetch_credentials(await connect_op()),
            PurePath(config["download_directory"]),
        )

    asyncio.run(run())


@cli.command()
def pull_finpension() -> None:
    """Prints Finpension’s portfolio total.

    It will print a line with the value like "12123.12\n"."""

    async def run():
        async with async_playwright() as pw:
            browser = await pw.firefox.launch(headless=False)
            page = await browser.new_page()
            await finpension.login(
                page, await finpension.fetch_credentials(await connect_op())
            )
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
        result[row["key"]] = row["value"]
    return result


@cli.command()
def ib_cancel_pending_deposits() -> None:
    """Cancels all pending deposits.

    Outputs a CSV with wire instructions.

    Example use:

        ib-cancel-pending-deposits
    """

    async def run():
        credentials = await ib.fetch_credentials(await connect_op())
        async with playwrightutils.new_page(Browser.FIREFOX, headless=False) as page:
            await ib.login(page, credentials)
            await ib.cancel_pending_deposits(page)

    asyncio.run(run())


@cli.command()
def ib_activity_pull() -> None:
    """Pulls Interactive Brokers' activity statement.

    Outputs the statement CSV to stdout.
    """
    downloads_path = Path("/tmp")

    async def run():
        credentials = await ib.fetch_credentials(await connect_op())
        async with playwrightutils.new_page(
            Browser.FIREFOX, headless=False, downloads_path=downloads_path
        ) as page:
            await ib.login(page, credentials)
            statement = await ib.fetch_statement(page, ib.StatementType.ACTIVITY)
            sys.stdout.buffer.write(statement)

    asyncio.run(run())


@cli.command()
@click.option(
    "--source", required=True, type=click.Choice(["CS", "BCGE"], case_sensitive=False)
)
@click.option("--amount", required=True)
def ib_set_up_incoming_deposit(source, amount) -> None:
    """Sets up an incoming deposit on Interactive Brokers.

    Outputs a CSV with wire instructions.

    Example use:

        ib-set-up-incoming-deposit --source=cs --amount=21.37
    """
    ib_source: ib.DepositSource = (
        ib.DepositSource.BCGE if source == "BCGE" else ib.DepositSource.CHARLES_SCHWAB
    )

    async def run() -> ib.SourceBankDepositInformation:
        credentials: ib.Credentials = await ib.fetch_credentials(await connect_op())
        async with playwrightutils.new_page(Browser.FIREFOX, headless=False) as page:
            await ib.login(page, credentials)
            instructions: ib.SourceBankDepositInformation = await ib.deposit(
                page, ib_source, decimal.Decimal(amount)
            )
            return instructions

    instructions = asyncio.run(run())

    writer = csv.DictWriter(sys.stdout, fieldnames=["key", "value"], delimiter=",")
    writer.writeheader()
    writer.writerow(
        {
            "key": "transfer_to",
            "value": instructions.transfer_to,
        }
    )
    writer.writerow(
        {
            "key": "iban",
            "value": instructions.iban,
        }
    )
    writer.writerow(
        {
            "key": "beneficiary_bank",
            "value": instructions.beneficiary_bank,
        }
    )
    writer.writerow(
        {
            "key": "for_further_credit",
            "value": instructions.for_further_credit,
        }
    )


@cli.command()
def pull_mbank() -> None:
    """Fetches mBank's data and outputs a CSV file."""

    async def run():
        creds = await mbank.fetch_credentials(await connect_op())
        async with playwrightutils.new_page(Browser.FIREFOX) as p:
            statement = await mbank.login_and_fetch_history(p, creds)
        sys.stdout.buffer.write(statement)

    asyncio.run(run())


@cli.command()
@click.option(
    "--download-directory",
    required=True,
    help="The target download directory.",
    type=click.Path(exists=True, file_okay=False, writable=True),
)
@click.pass_context
def revolut_pull(ctx, download_directory) -> None:
    """Fetches Revolut data into CSV files."""
    config = read_config_from_context(ctx)
    download_directory = Path(download_directory)

    async def run():
        async with playwrightutils.new_page(
            browser_type=Browser.FIREFOX, downloads_path=download_directory
        ) as p:
            await revolut.login_and_download_statements(
                p, download_directory, config["revolut_currencies"]
            )

    asyncio.run(run())


@cli.command()
def pull_splitwise() -> None:
    """Fetches the Splitwise statement."""

    async def run():
        creds = await splitwise.fetch_credentials(await connect_op())
        csv = splitwise.export_balances_to_csv(splitwise.fetch_balances(creds))
        sys.stdout.buffer.write(csv)

    asyncio.run(run())


@cli.command()
@click.pass_context
def pull_galaxus(ctx) -> None:
    """Fetches Digitec-Galaxus receipts in text format."""
    config = ctx.obj["config"]
    download_directory = PurePath(config["download_directory"])

    async def run():
        with contextlib.closing(
            gmail.connect(await gmail.fetch_credentials(await connect_op()))
        ) as inbox:
            for bill in galaxus.fetch_and_archive_bills(inbox):
                with open(download_directory / (bill.subject + ".galaxus"), "w") as f:
                    f.write(bill.payload)

    asyncio.run(run())


@cli.command()
@click.pass_context
def pull_google_play_mail(ctx) -> None:
    """Fetches Google Play receipts in text format."""
    config = ctx.obj["config"]
    download_directory = PurePath(config["download_directory"])

    async def run():
        with contextlib.closing(
            gmail.connect(await gmail.fetch_credentials(await connect_op()))
        ) as inbox:
            for bill in google_play_mail.fetch_and_archive_bills(inbox):
                with open(download_directory / (bill.subject + ".email"), "w") as f:
                    f.write(bill.payload)

    asyncio.run(run())


@cli.command()
@click.pass_context
def pull_patreon(ctx) -> None:
    """Fetches Patreon receipts in text format."""
    config = ctx.obj["config"]

    async def run():
        patreon.fetch_and_archive_receipts(
            await gmail.fetch_credentials(await connect_op()),
            PurePath(config["download_directory"]),
        )

    asyncio.run(run())


@cli.command()
@click.pass_context
def pull_uber_eats(ctx) -> None:
    """Fetches Uber Eats receipts in text format."""
    config = ctx.obj["config"]
    download_dir = PurePath(config["download_directory"])

    async def run():
        for title, content in ubereats.fetch_and_archive_bills(
            await gmail.fetch_credentials(await connect_op())
        ):
            with open(download_dir / (title + ".ubereats"), "w") as f:
                f.write(content)

    asyncio.run(run())


async def connect_op() -> op.OpSdkClient:
    op_service_account_auth_token = op.fetch_service_account_auth_token()
    return await op.OpSdkClient.connect(
        service_account_auth_token=op_service_account_auth_token
    )


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
