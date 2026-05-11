from services.news_service import NewsService


class FakeResponse:
    def __init__(self, status_code=200, content=b"<rss />", json_data=None, text=""):
        self.status_code = status_code
        self.content = content
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data


class FakeFeed:
    bozo = False
    bozo_exception = None
    entries = [
        {
            "title": "Bitcoin education update",
            "link": "https://example.com/btc",
            "summary": "Crypto learning and market structure.",
            "published": "Mon, 01 Jan 2024 00:00:00 GMT",
        },
        {
            "title": "Ethereum builders ship app",
            "link": "https://example.com/eth",
            "summary": "Smart contract news for Web3 developers.",
            "published": "Mon, 01 Jan 2024 00:00:00 GMT",
        },
        {
            "title": "Duplicate Bitcoin education update",
            "link": "https://example.com/btc",
            "summary": "This duplicate should be skipped.",
            "published": "Mon, 01 Jan 2024 00:00:00 GMT",
        },
    ]


def test_news_article_parsing_filters_title_and_dedupes(monkeypatch):
    service = NewsService()
    service.rss_feeds = {"Fake": "https://example.com/feed"}
    monkeypatch.setattr("services.news_service.requests.get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr("services.news_service.feedparser.parse", lambda content: FakeFeed())

    articles = service.fetch_latest_news(query="bitcoin", limit=5)

    assert len(articles) == 1
    assert articles[0]["title"] == "Bitcoin education update"
    assert articles[0]["source"] == "Fake"


def test_query_aliases_and_summary_search(monkeypatch):
    service = NewsService()
    service.rss_feeds = {"Fake": "https://example.com/feed"}
    monkeypatch.setattr("services.news_service.requests.get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr("services.news_service.feedparser.parse", lambda content: FakeFeed())

    articles = service.fetch_latest_news(query="etherium", limit=5)

    assert len(articles) == 1
    assert articles[0]["title"] == "Ethereum builders ship app"
    assert service.normalize_query("btc") == "bitcoin"
    assert service.normalize_query("web 3") == "web3"


def test_broad_query_does_not_over_filter(monkeypatch):
    service = NewsService()
    service.rss_feeds = {"Fake": "https://example.com/feed"}
    monkeypatch.setattr("services.news_service.requests.get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr("services.news_service.feedparser.parse", lambda content: FakeFeed())

    articles = service.fetch_latest_news(query="crypto", limit=5)

    assert len(articles) == 2


def test_google_fallback_when_rss_empty(monkeypatch):
    service = NewsService()
    service.rss_feeds = {"Fake": "https://example.com/feed"}

    def fake_get(url, **kwargs):
        if "googleapis" in url:
            return FakeResponse(
                json_data={
                    "items": [
                        {
                            "title": "Latest Web3 search result",
                            "displayLink": "example.com",
                            "link": "https://example.com/google",
                            "snippet": "A Google fallback result.",
                        }
                    ]
                }
            )
        return FakeResponse(status_code=500, text="rss down")

    monkeypatch.setattr("services.news_service.GOOGLE_SEARCH_API_KEY", "key")
    monkeypatch.setattr("services.news_service.GOOGLE_SEARCH_ENGINE_ID", "engine")
    monkeypatch.setattr("services.news_service.requests.get", fake_get)

    articles = service.fetch_latest_news(query="solana", limit=5)

    assert len(articles) == 1
    assert articles[0]["source"] == "example.com"


def test_clean_summary_limits_html_text():
    service = NewsService()
    summary = service.clean_summary("<p>" + ("hello " * 100) + "</p>", max_length=20)
    assert summary.endswith("...")
    assert len(summary) <= 23
