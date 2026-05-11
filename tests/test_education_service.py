from database.seed_data import seed_all
from services.education_service import get_lesson, get_glossary_term, get_beginner_roadmap


def test_lesson_fetching_from_seed_or_file():
    seed_all()
    lesson = get_lesson("bitcoin")
    assert lesson is not None
    assert "Bitcoin" in lesson["content"]


def test_glossary_fetching():
    seed_all()
    term = get_glossary_term("Wallet")
    assert term is not None
    assert "key" in term["definition"].lower()


def test_beginner_roadmap_has_risk_stage():
    roadmap = get_beginner_roadmap()
    assert any("Risk" in stage["title"] for stage in roadmap)
