"""Base repository interface."""

from typing import Generic, Protocol, TypeVar

T = TypeVar("T")


class Repository(Protocol[T]):
    """Repository protocol for domain objects."""

    async def get(self, id: str) -> T | None:
        """Get object by ID."""
        ...

    async def save(self, obj: T) -> T:
        """Save object."""
        ...

    async def delete(self, id: str) -> bool:
        """Delete object by ID."""
        ...


class AsyncRepository(Generic[T]):
    """Async repository base class."""

    def __init__(self) -> None:
        self._store: dict[str, T] = {}

    async def get(self, id: str) -> T | None:
        """Get object by ID from in-memory store."""
        return self._store.get(id)

    async def save(self, obj: T) -> T:
        """Save object to in-memory store.

        Requires obj to have an 'id' attribute or property.
        """
        obj_id = str(getattr(obj, "id", getattr(obj, "session_id", None)))
        if obj_id is None:
            raise ValueError("Object must have 'id' or 'session_id' attribute")
        self._store[obj_id] = obj
        return obj

    async def delete(self, id: str) -> bool:
        """Delete object from in-memory store."""
        if id in self._store:
            del self._store[id]
            return True
        return False
