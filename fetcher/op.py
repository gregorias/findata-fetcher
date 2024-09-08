"""A wrapper for the 1Password CLI."""
import contextlib
import os
import subprocess
from typing import Iterator

from onepassword.client import Client  # type: ignore

# The vault where the 1Password items accessible by the findata service account
# are stored.
FINDATA_VAULT = "Automated Findata"


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


# Can’t use the SDK, because there’s [a bug](https://github.com/1Password/onepassword-sdk-python/issues/108).
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


class OpSdkClient():
    """A wrapper for the 1Password SDK client."""

    def __init__(self, op_sdk_client: Client):
        self._op_sdk_client = op_sdk_client

    @staticmethod
    async def connect(service_account_auth_token: str) -> 'OpSdkClient':
        """Creates a new 1Password SDK client and authenticates it."""
        client = await Client.authenticate(auth=service_account_auth_token,
                                           integration_name="Findata Fetcher",
                                           integration_version="1.0.0")
        return OpSdkClient(client)

    async def read(self, vault: str, item: str, field: str) -> str:
        """Reads a field from an item in a vault."""
        return await self._op_sdk_client.secrets.resolve(
            f"op://{vault}/{item}/{field}")

    async def get_vault_id(self, vault_name: str) -> str | None:
        async for vault in await self._op_sdk_client.vaults.list_all():
            if vault.title == vault_name:
                return vault.id
        return None

    async def get_item_id(self, vault_id, item_name: str) -> str | None:
        async for item in await self._op_sdk_client.items.list_all(vault_id):
            if item.title == item_name:
                return item.id
        return None
