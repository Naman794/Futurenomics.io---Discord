import json
from pathlib import Path

from config import BASE_DIR
from database.db import execute_query, fetch_one, init_db


LESSON_TITLES = {
    "bitcoin": "Bitcoin Basics",
    "ethereum": "Ethereum Basics",
    "wallets": "Wallets and Self-Custody",
    "gas_fees": "Gas Fees",
    "defi": "DeFi Basics",
}


def seed_lessons() -> None:
    for path in (BASE_DIR / "data" / "lessons").glob("*.md"):
        slug = path.stem
        execute_query(
            """
            INSERT OR IGNORE INTO lessons(topic_slug, title, category, level, content)
            VALUES (?, ?, ?, ?, ?)
            """,
            (slug, LESSON_TITLES.get(slug, slug.replace("_", " ").title()), "web3", "beginner", path.read_text(encoding="utf-8")),
        )


def seed_glossary() -> None:
    glossary_path = BASE_DIR / "data" / "glossary.json"
    terms = json.loads(glossary_path.read_text(encoding="utf-8"))
    for item in terms:
        execute_query(
            """
            INSERT OR IGNORE INTO glossary(term, definition, category, example)
            VALUES (?, ?, ?, ?)
            """,
            (item["term"], item["definition"], item.get("category"), item.get("example")),
        )


def seed_quizzes() -> None:
    if fetch_one("SELECT id FROM quizzes WHERE question = ?", ("What is the maximum supply of Bitcoin?",)):
        return
    execute_query(
        """
        INSERT OR IGNORE INTO quizzes(lesson_id, question, option_a, option_b, option_c, option_d, correct_option, explanation)
        VALUES ((SELECT id FROM lessons WHERE topic_slug = 'bitcoin'), ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "What is the maximum supply of Bitcoin?",
            "21 million",
            "100 million",
            "Unlimited",
            "1 billion",
            "A",
            "Bitcoin's issuance schedule caps supply at 21 million BTC.",
        ),
    )


def seed_all() -> None:
    init_db()
    seed_lessons()
    seed_glossary()
    seed_quizzes()


if __name__ == "__main__":
    seed_all()
