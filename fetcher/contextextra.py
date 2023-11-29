"""Extra utilties for context managers."""

from contextlib import asynccontextmanager
import typing


class AsyncClosable(typing.Protocol):
    """A protocol for objects that can be closed asynchronously."""

    async def close(self) -> None:
        """Close the object asynchronously."""
        ...


T = typing.TypeVar('T', bound=AsyncClosable)


@asynccontextmanager
async def async_closing(thing: T) -> typing.AsyncIterator[T]:
    """Like contextlib.closing but for objects with async close functions."""
    try:
        yield thing
    finally:
        await thing.close()
