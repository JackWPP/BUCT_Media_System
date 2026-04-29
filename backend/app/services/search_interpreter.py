"""
Search interpreter engine — the core infrastructure for smart search.

Provides rule-based (alias matching) and AI-based query interpretation,
with graceful fallback to plain keyword search.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.taxonomy import TaxonomyAlias, TaxonomyFacet, TaxonomyNode

logger = logging.getLogger(__name__)

_STOP_WORDS = frozenset("的了里在中和与或及从到被把让给向往上下大小多少新旧好美")
_PARTICLES = re.compile(r"[的了吗呢吧啊呀哦哇嘛咯]")


@dataclass
class TokenMatch:
    facet_key: str
    facet_name: str
    node_name: str
    matched_text: str
    match_source: str  # "node_name" | "alias"


@dataclass
class SearchInterpretation:
    facet_filters: dict[str, str] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)
    original_query: str = ""
    method: str = "fallback"
    confidence: float = 0.0
    explanation: str | None = None
    ai_raw_response: dict | None = None

    @property
    def is_empty(self) -> bool:
        return not self.facet_filters and not self.keywords


class AliasIndex:
    """In-memory reverse index: alias text → taxonomy node, auto-refreshed from DB."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._alias_map: dict[str, list[TokenMatch]] = {}
        self._node_name_map: dict[str, list[TokenMatch]] = {}
        self._all_keys_sorted: list[str] = []
        self._loaded_at: datetime | None = None
        self._ttl = timedelta(seconds=ttl_seconds)

    @property
    def is_loaded(self) -> bool:
        return self._loaded_at is not None

    @property
    def is_stale(self) -> bool:
        if self._loaded_at is None:
            return True
        return datetime.utcnow() - self._loaded_at > self._ttl

    @property
    def taxonomy_schema(self) -> dict[str, Any]:
        facets: dict[str, Any] = {}
        seen: set[str] = set()
        for key, matches in self._node_name_map.items():
            for m in matches:
                if m.facet_key not in facets:
                    facets[m.facet_key] = {"name": m.facet_name, "nodes": []}
                node_entry = m.node_name
                if node_entry not in seen:
                    facets[m.facet_key]["nodes"].append(node_entry)
                    seen.add(node_entry)
        for alias_text, matches in self._alias_map.items():
            for m in matches:
                if m.facet_key not in facets:
                    facets[m.facet_key] = {"name": m.facet_name, "nodes": []}
        return facets

    async def build(self, db: AsyncSession) -> None:
        result = await db.execute(
            select(TaxonomyFacet, TaxonomyNode, TaxonomyAlias)
            .join(TaxonomyNode, TaxonomyNode.facet_id == TaxonomyFacet.id)
            .outerjoin(TaxonomyAlias, TaxonomyAlias.node_id == TaxonomyNode.id)
            .where(TaxonomyFacet.is_active.is_(True), TaxonomyNode.is_active.is_(True))
            .order_by(TaxonomyFacet.sort_order, TaxonomyNode.sort_order)
        )
        rows = result.all()

        alias_map: dict[str, list[TokenMatch]] = {}
        node_name_map: dict[str, list[TokenMatch]] = {}

        for facet, node, alias in rows:
            match = TokenMatch(
                facet_key=facet.key,
                facet_name=facet.name,
                node_name=node.name,
                matched_text=node.name,
                match_source="node_name",
            )
            node_name_lower = node.name.lower().strip()
            if node_name_lower not in node_name_map:
                node_name_map[node_name_lower] = []
            if match not in node_name_map[node_name_lower]:
                node_name_map[node_name_lower].append(match)

            if alias and alias.alias:
                alias_match = TokenMatch(
                    facet_key=facet.key,
                    facet_name=facet.name,
                    node_name=node.name,
                    matched_text=alias.alias,
                    match_source="alias",
                )
                alias_lower = alias.alias.lower().strip()
                if alias_lower not in alias_map:
                    alias_map[alias_lower] = []
                if alias_match not in alias_map[alias_lower]:
                    alias_map[alias_lower].append(alias_match)

        self._alias_map = alias_map
        self._node_name_map = node_name_map
        all_keys = set(alias_map.keys()) | set(node_name_map.keys())
        self._all_keys_sorted = sorted(all_keys, key=len, reverse=True)
        self._loaded_at = datetime.utcnow()
        logger.info(
            "AliasIndex built: %d aliases, %d node names, %d total keys",
            len(alias_map),
            len(node_name_map),
            len(self._all_keys_sorted),
        )

    async def refresh_if_stale(self, db: AsyncSession) -> None:
        if self.is_stale:
            await self.build(db)

    def match(self, query: str) -> tuple[list[TokenMatch], list[str]]:
        tokens = self._tokenize(query)
        used_spans: list[tuple[int, int]] = []
        matches: list[TokenMatch] = []

        for token in tokens:
            token_lower = token.lower().strip()
            if not token_lower:
                continue

            found = self._lookup(token_lower)
            if found:
                for m in found:
                    if m.facet_key not in [existing.facet_key for existing in matches]:
                        matches.append(m)

        remaining = self._extract_remaining(query, matches)
        return matches, remaining

    def _tokenize(self, query: str) -> list[str]:
        cleaned = _PARTICLES.sub("", query)
        parts = re.split(r"[\s,，、；;：:！!？?·\-\|]+", cleaned)
        tokens: list[str] = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            tokens.append(part)
            if len(part) >= 4:
                tokens.append(part[:3])
                tokens.append(part[:2])
            elif len(part) == 3:
                tokens.append(part[:2])
        return tokens

    def _lookup(self, token_lower: str) -> list[TokenMatch] | None:
        if token_lower in self._node_name_map:
            return self._node_name_map[token_lower]
        if token_lower in self._alias_map:
            return self._alias_map[token_lower]
        return None

    def _extract_remaining(self, query: str, matches: list[TokenMatch]) -> list[str]:
        remaining = query
        for m in matches:
            remaining = remaining.replace(m.matched_text, "", 1)
            if m.node_name != m.matched_text:
                remaining = remaining.replace(m.node_name, "", 1)
        remaining = _PARTICLES.sub("", remaining)
        words = re.split(r"[\s,，、；;：:！!？?·\-\|]+", remaining)
        return [w.strip() for w in words if w.strip() and len(w.strip()) > 0]


class SearchInterpreter:
    """Search interpretation engine — pluggable, zero-hardcoded infrastructure."""

    def __init__(self) -> None:
        self._alias_index = AliasIndex()
        self._ai_cache: dict[str, SearchInterpretation] = {}
        self._ai_cache_max = 200

    @property
    def alias_index(self) -> AliasIndex:
        return self._alias_index

    async def interpret(self, query: str, db: AsyncSession) -> SearchInterpretation:
        if not query or not query.strip():
            return SearchInterpretation(original_query=query, method="fallback", confidence=0.0)

        query = query.strip()

        await self._alias_index.refresh_if_stale(db)
        if not self._alias_index.is_loaded:
            await self._alias_index.build(db)

        rule_result = self._rule_interpret(query)
        if rule_result and rule_result.facet_filters:
            return rule_result

        ai_result = await self._ai_interpret(query, db)
        if ai_result and (ai_result.facet_filters or ai_result.keywords != [query]):
            return ai_result

        return SearchInterpretation(
            facet_filters={},
            keywords=[query],
            original_query=query,
            method="fallback",
            confidence=0.3,
            explanation=f"关键词搜索: {query}",
        )

    def _rule_interpret(self, query: str) -> SearchInterpretation | None:
        matches, remaining = self._alias_index.match(query)

        if not matches:
            keywords = [w for w in remaining if w] if remaining else [query]
            return SearchInterpretation(
                facet_filters={},
                keywords=keywords,
                original_query=query,
                method="rule",
                confidence=0.2,
                explanation=None,
            )

        facet_filters: dict[str, str] = {}
        for m in matches:
            if m.facet_key not in facet_filters:
                facet_filters[m.facet_key] = m.node_name

        explanation_parts = []
        for key, value in facet_filters.items():
            facet_match = next(m for m in matches if m.facet_key == key)
            facet_name = facet_match.facet_name
            explanation_parts.append(f"{facet_name}={value}")
        if remaining:
            explanation_parts.append(f"关键词: {', '.join(remaining)}")

        confidence = min(0.9, 0.5 + len(facet_filters) * 0.15)

        return SearchInterpretation(
            facet_filters=facet_filters,
            keywords=[w for w in remaining if w],
            original_query=query,
            method="rule",
            confidence=confidence,
            explanation=", ".join(explanation_parts) if explanation_parts else None,
        )

    async def _ai_interpret(self, query: str, db: AsyncSession) -> SearchInterpretation | None:
        cached = self._ai_cache.get(query)
        if cached:
            return cached

        try:
            from app.services.ai_providers import ResolvedAIProvider, resolve_db_providers, resolve_env_provider
            from app.services.runtime_settings import get_runtime_settings
            from app.prompts.search_rewrite import build_search_rewrite_prompt, parse_rewrite_response

            runtime_settings = await get_runtime_settings(db)
            if not runtime_settings.ai_search_enabled:
                return None

            providers = await resolve_db_providers(db)

            search_provider_type = runtime_settings.ai_search_provider
            search_model_id = runtime_settings.ai_search_model_id
            search_timeout = runtime_settings.ai_search_timeout

            if search_provider_type and search_model_id:
                if providers:
                    matched = next(
                        (p for p in providers if p.provider_type == search_provider_type),
                        None,
                    )
                    if matched:
                        providers = [
                            ResolvedAIProvider(
                                provider_type=matched.provider_type,
                                display_name=matched.display_name,
                                base_url=matched.base_url,
                                model_id=search_model_id,
                                api_key=matched.api_key,
                                extra_headers=matched.extra_headers,
                                timeout_seconds=search_timeout,
                                max_retries=matched.max_retries,
                                daily_budget=matched.daily_budget,
                                source=matched.source,
                                provider_id=matched.provider_id,
                            ),
                        ]
                    else:
                        env_fallback = resolve_env_provider(search_provider_type, search_model_id)
                        if env_fallback:
                            env_fallback = ResolvedAIProvider(
                                provider_type=env_fallback.provider_type,
                                display_name=env_fallback.display_name,
                                base_url=env_fallback.base_url,
                                model_id=search_model_id,
                                api_key=env_fallback.api_key,
                                extra_headers=env_fallback.extra_headers,
                                timeout_seconds=search_timeout,
                                max_retries=env_fallback.max_retries,
                                daily_budget=env_fallback.daily_budget,
                                source=env_fallback.source,
                                provider_id=env_fallback.provider_id,
                            )
                            providers = [env_fallback]
                else:
                    env_fallback = resolve_env_provider(search_provider_type, search_model_id)
                    if env_fallback:
                        env_fallback = ResolvedAIProvider(
                            provider_type=env_fallback.provider_type,
                            display_name=env_fallback.display_name,
                            base_url=env_fallback.base_url,
                            model_id=search_model_id,
                            api_key=env_fallback.api_key,
                            extra_headers=env_fallback.extra_headers,
                            timeout_seconds=search_timeout,
                            max_retries=env_fallback.max_retries,
                            daily_budget=env_fallback.daily_budget,
                            source=env_fallback.source,
                            provider_id=env_fallback.provider_id,
                        )
                        providers = [env_fallback]
            elif not providers:
                env_provider = resolve_env_provider(
                    runtime_settings.ai_provider,
                    runtime_settings.ai_model_id,
                )
                if env_provider:
                    providers = [env_provider]

            if not providers:
                return None

            taxonomy_schema = self._alias_index.taxonomy_schema
            prompt = build_search_rewrite_prompt(query, taxonomy_schema)

            from app.services.ai_tagging import OllamaProvider, OpenAICompatibleProvider, DashScopeVLMProvider

            for provider_config in providers:
                if provider_config.provider_type == "ollama":
                    provider = OllamaProvider(provider_config)
                elif provider_config.provider_type == "dashscope":
                    provider = DashScopeVLMProvider(provider_config)
                else:
                    provider = OpenAICompatibleProvider(provider_config)

                try:
                    response_text = await provider.analyze_text(prompt)
                    if response_text:
                        result = parse_rewrite_response(response_text, query, taxonomy_schema)
                        if result:
                            self._put_cache(query, result)
                            return result
                except Exception as exc:
                    logger.warning("AI search rewrite provider %s failed: %s", provider_config.provider_type, exc)
                    continue

        except Exception as exc:
            logger.warning("AI search rewrite failed: %s", exc)

        return None

    def _put_cache(self, query: str, result: SearchInterpretation) -> None:
        if len(self._ai_cache) >= self._ai_cache_max:
            oldest_key = next(iter(self._ai_cache))
            del self._ai_cache[oldest_key]
        self._ai_cache[query] = result


_interpreter: SearchInterpreter | None = None


def get_search_interpreter() -> SearchInterpreter:
    global _interpreter
    if _interpreter is None:
        _interpreter = SearchInterpreter()
    return _interpreter
