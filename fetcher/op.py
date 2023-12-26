"""A wrapper for the 1Password CLI."""

import contextlib
import os
import subprocess
from typing import Iterator


@contextlib.contextmanager
def set_service_account_auth_token(
        service_account_auth_token: str) -> Iterator[None]:
    """Sets the service account auth token for the duration of the context."""
    OP_SERVICE_ACCOUNT_TOKEN = 'OP_SERVICE_ACCOUNT_TOKEN'
    previous_op_service_account_token = os.environ.get(
        OP_SERVICE_ACCOUNT_TOKEN)
    try:
        os.environ[OP_SERVICE_ACCOUNT_TOKEN] = service_account_auth_token
        yield None
    finally:
        if previous_op_service_account_token is None:
            del os.environ[OP_SERVICE_ACCOUNT_TOKEN]
        else:
            os.environ[
                OP_SERVICE_ACCOUNT_TOKEN] = previous_op_service_account_token


class OpError(Exception):
    """An error from the 1Password CLI."""

    def __init__(self, message: str):
        super().__init__(message)


def read(vault: str, item: str, field: str) -> str:
    """Fetches a field from an item in a vault."""
    field = f"op://{vault}/{item}/{field}"
    op_read = subprocess.run(["op", "read", field, "--no-newline"],
                             capture_output=True,
                             text=True)
    if op_read.returncode != 0:
        raise OpError(
            f"Could not read {field}. 1Password outputted: f{op_read.stderr}")
    return op_read.stdout


def fetch_totp(vault: str, item: str) -> str:
    """Fetches a TOTP of an item in a vault."""
    op_read = subprocess.run(
        ["op", "item", "get", "--otp", f"--vault={vault}", item],
        capture_output=True,
        text=True)
    if op_read.returncode != 0:
        raise OpError(
            f"Could not read TOTP. 1Password outputted: f{op_read.stderr}")
    return op_read.stdout
