"""Extra utilties for context managers."""

from contextlib import asynccontextmanager


@asynccontextmanager
async def async_closing(factory):
    thing = await factory
    try:
        yield thing
    finally:
        await thing.close()
