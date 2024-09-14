"""A wrapper for the 1Password CLI."""
import subprocess

from onepassword.client import Client  # type: ignore

# The vault where the 1Password items accessible by the findata service account
# are stored.
FINDATA_VAULT = "Automated Findata"


def fetch_service_account_auth_token() -> str:
    """Fetches the 1Password service account auth token for Findata.

    This function uses the `op` command line tool.

    Returns:
        The 1Password service account auth token.

    Raises:
        Exception: If the 1Password service account auth token could not be
            fetched.
    """
    # op item get --vault="Automated Findata" "Service Account Auth Token Findata" --reveal --fields label="credential"
    op_read = subprocess.run([
        "op", "item", "get", "--vault", FINDATA_VAULT,
        "Service Account Auth Token Findata", "--reveal", "--fields",
        "label=credential"
    ],
                             capture_output=True,
                             text=True)
    if op_read.returncode != 0:
        raise Exception(
            "Could not fetch the 1Password service account auth token.")
    return op_read.stdout.strip()


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

    async def get_totp(self, vault_id, item_id) -> str:
        """Fetches the TOTP of an item in a vault.

        Raises:
            Exception: If the TOTP could not be fetched.
        """
        item = await self._op_sdk_client.items.get(vault_id, item_id)
        for f in item.fields:
            if f.field_type == "Totp":
                if f.details.content.error_message is not None:
                    raise Exception(
                        f'Could not fetch Totp: {f.details.content.error_message}.'
                    )
                else:
                    return f.details.content.code
        raise Exception(
            "Could not find the TOTP field for the 1Password item.")
