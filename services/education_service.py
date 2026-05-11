import json
import random

from config import BASE_DIR
from database.db import fetch_all, fetch_one


def _slug(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def get_lesson(topic: str) -> dict | None:
    slug = _slug(topic)
    row = fetch_one("SELECT * FROM lessons WHERE topic_slug = ?", (slug,))
    if row:
        return row
    path = BASE_DIR / "data" / "lessons" / f"{slug}.md"
    if path.exists():
        return {"topic_slug": slug, "title": slug.replace("_", " ").title(), "content": path.read_text(encoding="utf-8")}
    return None


def get_glossary_term(term: str) -> dict | None:
    row = fetch_one("SELECT * FROM glossary WHERE lower(term) = lower(?)", (term.strip(),))
    if row:
        return row
    for item in json.loads((BASE_DIR / "data" / "glossary.json").read_text(encoding="utf-8")):
        if item["term"].lower() == term.strip().lower():
            return item
    return None


def get_beginner_roadmap() -> list[dict]:
    return json.loads((BASE_DIR / "data" / "beginner_roadmap.json").read_text(encoding="utf-8"))


def get_quiz(level: str = "beginner") -> dict | None:
    rows = fetch_all(
        """
        SELECT q.* FROM quizzes q
        LEFT JOIN lessons l ON q.lesson_id = l.id
        WHERE COALESCE(l.level, ?) = ?
        """,
        (level, level),
    )
    return random.choice(rows) if rows else None


def list_lessons() -> list[dict]:
    rows = fetch_all("SELECT topic_slug, title, category, level FROM lessons ORDER BY title")
    if rows:
        return rows
    return [{"topic_slug": p.stem, "title": p.stem.replace("_", " ").title(), "level": "beginner"} for p in (BASE_DIR / "data" / "lessons").glob("*.md")]


def list_glossary_terms() -> list[str]:
    rows = fetch_all("SELECT term FROM glossary ORDER BY term")
    if rows:
        return [row["term"] for row in rows]
    return [item["term"] for item in json.loads((BASE_DIR / "data" / "glossary.json").read_text(encoding="utf-8"))]
