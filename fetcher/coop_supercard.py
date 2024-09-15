"""Fetches Coop receipts from supercard.ch."""

ORDER_PAGE = 'https://www.coop.ch/de/my-orders'

__all__ = [
    'fetch_receipts_manually',
]


def fetch_receipts_manually() -> None:
    """Opens the Coop order page in the default browser."""
    import subprocess
    subprocess.run(['open', ORDER_PAGE])
