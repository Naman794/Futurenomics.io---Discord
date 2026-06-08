import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from config import BASE_DIR

KNOWLEDGE_BASE_PATH = BASE_DIR / "data" / "knowledge_base" / "futurenomics_crypto_intel_dictionary.json"
DISCLAIMER = "Educational context only. Verify live data before acting. Not financial advice."


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9$]+", " ", value.lower()).strip()


def _tokens(value: str) -> set[str]:
    return {token for token in _normalize(value).split() if len(token) >= 2}


class IntelService:
    def __init__(self, path: Path = KNOWLEDGE_BASE_PATH) -> None:
        self.path = path

    @lru_cache(maxsize=1)
    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"metadata": {}, "articles": [], "market_briefs": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def articles(self) -> list[dict]:
        return list(self.load().get("articles", []))

    def market_briefs(self) -> list[dict]:
        return list(self.load().get("market_briefs", []))

    def search(self, query: str, limit: int = 5) -> list[dict]:
        query = query.strip()
        if not query:
            return []

        scored: list[tuple[int, dict]] = []
        for article in self.articles():
            score = self._score_article(query, article)
            if score > 0:
                scored.append((score, {**article, "kind": "article"}))

        for brief in self.market_briefs():
            score = self._score_brief(query, brief)
            if score > 0:
                scored.append((score, {**brief, "kind": "market_brief"}))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def best_match(self, query: str) -> dict | None:
        results = self.search(query, limit=1)
        return results[0] if results else None

    def context_match(self, query: str) -> dict | None:
        brief_scores = [(self._score_brief(query, brief), {**brief, "kind": "market_brief"}) for brief in self.market_briefs()]
        brief_scores = [(score, item) for score, item in brief_scores if score > 0]
        if brief_scores:
            brief_scores.sort(key=lambda item: item[0], reverse=True)
            return brief_scores[0][1]
        return self.best_match(query)

    def related(self, query: str, limit: int = 5) -> list[dict]:
        base = self.best_match(query)
        if not base:
            return self.search(query, limit=limit)

        base_terms = set()
        for field in ("keywords", "entities"):
            for value in base.get(field, []) or []:
                base_terms.update(_tokens(str(value)))
        base_terms.update(_tokens(base.get("title", "")))

        rows: list[tuple[int, dict]] = []
        for article in self.articles():
            if article.get("slug") == base.get("slug"):
                continue
            article_terms = set()
            for field in ("keywords", "entities"):
                for value in article.get(field, []) or []:
                    article_terms.update(_tokens(str(value)))
            article_terms.update(_tokens(article.get("title", "")))
            overlap = len(base_terms & article_terms)
            if overlap:
                rows.append((overlap, article))

        rows.sort(key=lambda item: item[0], reverse=True)
        return [item for _, item in rows[:limit]]

    def format_answer(self, item: dict) -> tuple[str, str]:
        if item.get("kind") == "market_brief":
            title = item.get("name", "Futurenomics Context")
            description = (
                f"**Simple read:**\n{item.get('summary', 'No summary available.')}\n\n"
                f"**Useful keywords:**\n{', '.join(item.get('keywords', [])[:8]) or 'N/A'}\n\n"
                f"_{DISCLAIMER}_"
            )
            return title, description

        title = item.get("title", "Futurenomics Intel")
        facts = item.get("key_facts", []) or []
        fact_lines = "\n".join(f"• {fact}" for fact in facts[:3]) or "• No key facts available."
        description = (
            f"**Quick answer:**\n{item.get('bot_response') or item.get('summary', 'No response available.')}\n\n"
            f"**Why it matters:**\n{item.get('angle', 'No angle available.')}\n\n"
            f"**Key facts:**\n{fact_lines}\n\n"
            f"_{DISCLAIMER}_"
        )
        return title, description

    def format_related(self, items: list[dict]) -> tuple[str, str]:
        if not items:
            return "Related Intel", "No related Futurenomics intel found yet."
        lines = []
        for index, item in enumerate(items, start=1):
            title = item.get("title") or item.get("name") or item.get("slug") or "Untitled"
            slug = item.get("slug")
            if slug:
                lines.append(f"{index}. **{title}**\n`{slug}`")
            else:
                lines.append(f"{index}. **{title}**")
        return "Related Futurenomics Intel", "\n\n".join(lines)

    def list_topics(self, limit: int = 20) -> list[str]:
        return [f"`{item.get('slug')}` - {item.get('title')}" for item in self.articles()[:limit]]

    def _score_article(self, query: str, article: dict) -> int:
        query_norm = _normalize(query)
        query_tokens = _tokens(query)
        searchable_parts = [
            article.get("slug", ""),
            article.get("title", ""),
            article.get("summary", ""),
            article.get("angle", ""),
            article.get("bot_response", ""),
            " ".join(article.get("keywords", []) or []),
            " ".join(article.get("entities", []) or []),
        ]
        searchable = _normalize(" ".join(searchable_parts))
        searchable_tokens = _tokens(searchable)

        score = len(query_tokens & searchable_tokens)
        if query_norm and query_norm in searchable:
            score += 8
        if query_norm == _normalize(article.get("slug", "")):
            score += 20
        for keyword in article.get("keywords", []) or []:
            if _normalize(keyword) in query_norm or query_norm in _normalize(keyword):
                score += 4
        for entity in article.get("entities", []) or []:
            if _normalize(entity) in query_norm or query_norm in _normalize(entity):
                score += 3
        return score

    def _score_brief(self, query: str, brief: dict) -> int:
        query_norm = _normalize(query)
        query_tokens = _tokens(query)
        searchable = _normalize(
            " ".join([
                brief.get("name", ""),
                brief.get("summary", ""),
                " ".join(brief.get("keywords", []) or []),
            ])
        )
        score = len(query_tokens & _tokens(searchable))
        if query_norm and query_norm in searchable:
            score += 8
        return score


intel_service = IntelService()
