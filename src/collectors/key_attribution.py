"""Resolve LiteLLM spend-log key references to the ``proxy_keys`` registry.

Per ADR-002, the LiteLLM virtual key reference carried on spend logs is used
only for lookup and is never persisted. Unresolved keys are reported by a
non-reversible fingerprint so operators can detect unattributed traffic.
"""

import hashlib
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from benchmark_core.db.models import ProxyKey as ProxyKeyORM

logger = logging.getLogger(__name__)


class ProxyKeyLookup(Protocol):
    """Subset of the proxy key repository used for attribution."""

    async def get_by_litellm_key_id(self, litellm_key_id: str) -> ProxyKeyORM | None: ...

    async def get_by_alias(self, key_alias: str) -> ProxyKeyORM | None: ...


@dataclass(frozen=True)
class KeyAttribution:
    """Registry attribution for one usage record."""

    proxy_key_id: UUID
    key_alias: str
    litellm_key_id: str | None
    owner: str | None
    team: str | None
    customer: str | None
    matched_by: str


def key_fingerprint(key_reference: str) -> str:
    """Return a short, non-reversible fingerprint for a key reference."""
    digest = hashlib.sha256(key_reference.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:12]}"


class ProxyKeyAttributionResolver:
    """Resolve spend-log key references to registry entries, with caching.

    Lookup order: registry ``litellm_key_id`` match on the spend-log key
    reference, then the operator-supplied ephemeral ``virtual_key_aliases``
    mapping (ADR-002 default mechanism), then the alias reported by LiteLLM.
    """

    def __init__(
        self,
        repository: ProxyKeyLookup,
        virtual_key_aliases: Mapping[str, str] | None = None,
    ) -> None:
        self._repository = repository
        self._virtual_key_aliases = dict(virtual_key_aliases or {})
        self._by_key_ref: dict[str, ProxyKeyORM | None] = {}
        self._by_alias: dict[str, ProxyKeyORM | None] = {}

    async def resolve(
        self,
        key_reference: str | None,
        reported_alias: str | None,
    ) -> KeyAttribution | None:
        """Resolve attribution for a record.

        Args:
            key_reference: LiteLLM key reference from the spend log (hashed
                ``api_key`` or ``metadata.user_api_key``). Lookup only.
            reported_alias: ``api_key_alias`` reported by LiteLLM, if any.

        Returns:
            Attribution when a registry entry matches, otherwise None.
        """
        if key_reference:
            orm = await self._lookup_key_ref(key_reference)
            if orm is not None:
                return self._to_attribution(orm, "litellm_key_id")
            mapped_alias = self._virtual_key_aliases.get(key_reference)
            if mapped_alias:
                orm = await self._lookup_alias(mapped_alias)
                if orm is not None:
                    return self._to_attribution(orm, "virtual_key_mapping")
        if reported_alias:
            orm = await self._lookup_alias(reported_alias)
            if orm is not None:
                return self._to_attribution(orm, "key_alias")
        logger.warning(
            "Usage record key not found in proxy_keys registry (key=%s, alias=%s)",
            key_fingerprint(key_reference) if key_reference else None,
            reported_alias,
        )
        return None

    async def _lookup_key_ref(self, key_reference: str) -> ProxyKeyORM | None:
        if key_reference not in self._by_key_ref:
            self._by_key_ref[key_reference] = await self._repository.get_by_litellm_key_id(
                key_reference
            )
        return self._by_key_ref[key_reference]

    async def _lookup_alias(self, alias: str) -> ProxyKeyORM | None:
        if alias not in self._by_alias:
            self._by_alias[alias] = await self._repository.get_by_alias(alias)
        return self._by_alias[alias]

    @staticmethod
    def _to_attribution(orm: ProxyKeyORM, matched_by: str) -> KeyAttribution:
        return KeyAttribution(
            proxy_key_id=orm.id,
            key_alias=orm.key_alias,
            litellm_key_id=orm.litellm_key_id,
            owner=orm.owner,
            team=orm.team,
            customer=orm.customer,
            matched_by=matched_by,
        )
