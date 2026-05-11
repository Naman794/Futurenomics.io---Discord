import logging
import re
from datetime import UTC, datetime
from typing import Dict, List, Optional
from urllib.parse import quote_plus

import requests

try:
    import feedparser
except ModuleNotFoundError:
    class _MissingFeedparser:
        missing = True

        @staticmethod
        def parse(content):
            logger.error("feedparser is not installed; RSS news fetching is unavailable.")
            print("[NEWS RSS ERROR] feedparser is not installed")
            return type("EmptyFeed", (), {"bozo": False, "entries": []})()

    feedparser = _MissingFeedparser()

from config import GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_ENGINE_ID
from database.db import execute_query

logger = logging.getLogger(__name__)

BROAD_QUERIES = {"crypto", "web3", "blockchain", "news"}


class NewsService:
    def __init__(self) -> None:
        self.rss_feeds = {
            "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
            "Cointelegraph": "https://cointelegraph.com/rss",
            "Decrypt": "https://decrypt.co/feed",
            "CryptoSlate": "https://cryptoslate.com/feed",
            "CryptoNews": "https://cryptonews.com/news/feed/",
            "The Defiant": "https://thedefiant.io/feed",
        }
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 FuturenomicsBot/1.0 "
                "(Private Discord Crypto Education Bot)"
            )
        }
        self.keyword_aliases = {
            "etherium": "ethereum",
            "eth": "ethereum",
            "btc": "bitcoin",
            "web 3": "web3",
        }

    def normalize_query(self, query: Optional[str]) -> str:
        if not query:
            return "crypto"
        query = " ".join(query.strip().lower().split())
        return self.keyword_aliases.get(query, query)

    def fetch_latest_news(self, query: str = "crypto", limit: int = 5) -> List[Dict]:
        query = self.normalize_query(query)
        articles = self.fetch_from_rss(query=query, limit=limit)
        if articles:
            logger.info("RSS returned %s article(s) for query=%s", len(articles), query)
            return articles[:limit]

        logger.info("RSS returned no articles for query=%s; trying Google fallback", query)
        articles = self.fetch_from_google(query=query, limit=limit)
        return articles[:limit]

    def fetch_from_rss(self, query: str = "crypto", limit: int = 5) -> List[Dict]:
        articles: List[Dict] = []
        seen_urls: set[str] = set()

        for source, feed_url in self.rss_feeds.items():
            try:
                response = requests.get(feed_url, headers=self.headers, timeout=12)
                if response.status_code != 200:
                    logger.warning("RSS HTTP error for %s: HTTP %s", source, response.status_code)
                    print(f"[NEWS RSS ERROR] {source}: HTTP {response.status_code}")
                    continue

                feed = feedparser.parse(response.content)
                if getattr(feed, "bozo", False):
                    warning = getattr(feed, "bozo_exception", "unknown parse warning")
                    logger.warning("RSS parse warning for %s: %s", source, warning)
                    print(f"[NEWS RSS PARSE WARNING] {source}: {warning}")

                for entry in getattr(feed, "entries", []):
                    title = self._entry_value(entry, "title").strip()
                    link = self._entry_value(entry, "link").strip()
                    summary = (
                        self._entry_value(entry, "summary")
                        or self._entry_value(entry, "description")
                        or self._entry_value(entry, "content")
                    ).strip()

                    if not title or not link:
                        continue

                    searchable_text = f"{title} {summary}".lower()
                    if query not in BROAD_QUERIES and query not in searchable_text:
                        continue

                    if link in seen_urls:
                        continue
                    seen_urls.add(link)

                    published = (
                        self._entry_value(entry, "published")
                        or self._entry_value(entry, "updated")
                        or ""
                    )
                    articles.append(
                        {
                            "title": title,
                            "source": source,
                            "url": link,
                            "summary": self.clean_summary(summary),
                            "published_at": published,
                        }
                    )

                    if len(articles) >= limit:
                        return articles

            except requests.RequestException as exc:
                logger.exception("RSS request exception for %s", source)
                print(f"[NEWS RSS EXCEPTION] {source}: {exc}")
            except Exception as exc:
                logger.exception("RSS exception for %s", source)
                print(f"[NEWS RSS EXCEPTION] {source}: {exc}")

        return articles

    def fetch_from_google(self, query: str = "crypto", limit: int = 5) -> List[Dict]:
        if not GOOGLE_SEARCH_API_KEY or not GOOGLE_SEARCH_ENGINE_ID:
            logger.warning("Google Search skipped: missing API key or Search Engine ID")
            print("[GOOGLE SEARCH SKIPPED] Missing API key or Search Engine ID")
            return []

        try:
            search_query = f"{query} crypto web3 latest news"
            url = (
                "https://www.googleapis.com/customsearch/v1"
                f"?key={GOOGLE_SEARCH_API_KEY}"
                f"&cx={GOOGLE_SEARCH_ENGINE_ID}"
                f"&q={quote_plus(search_query)}"
                f"&num={min(limit, 10)}"
            )
            response = requests.get(url, timeout=12)
            if response.status_code != 200:
                logger.warning("Google Search HTTP error: HTTP %s: %s", response.status_code, response.text)
                print(f"[GOOGLE SEARCH ERROR] HTTP {response.status_code}: {response.text}")
                return []

            articles: List[Dict] = []
            seen_urls: set[str] = set()
            for item in response.json().get("items", []):
                link = item.get("link", "")
                if not link or link in seen_urls:
                    continue
                seen_urls.add(link)
                articles.append(
                    {
                        "title": item.get("title", "Untitled"),
                        "source": item.get("displayLink", "Google Search"),
                        "url": link,
                        "summary": self.clean_summary(item.get("snippet", "")),
                        "published_at": datetime.now(UTC).isoformat(),
                    }
                )
            logger.info("Google Search returned %s article(s) for query=%s", len(articles), query)
            return articles

        except requests.RequestException as exc:
            logger.exception("Google Search request exception")
            print(f"[GOOGLE SEARCH EXCEPTION] {exc}")
            return []
        except Exception as exc:
            logger.exception("Google Search exception")
            print(f"[GOOGLE SEARCH EXCEPTION] {exc}")
            return []

    def clean_summary(self, summary: str, max_length: int = 240) -> str:
        if not summary:
            return "No summary available."
        if isinstance(summary, list):
            summary = " ".join(str(item) for item in summary)
        summary = re.sub(r"<[^>]+>", " ", str(summary))
        summary = re.sub(r"\s+", " ", summary).strip()
        if not summary:
            return "No summary available."
        if len(summary) > max_length:
            return summary[:max_length].rstrip() + "..."
        return summary

    def summarize_news(self, articles: List[Dict]) -> str:
        if not articles:
            return "No articles found right now."
        lines = []
        for index, article in enumerate(articles, start=1):
            lines.append(
                f"{index}. {article['title']} - {article['source']}\n"
                f"{article['url']}"
            )
        return "\n\n".join(lines)

    def save_article(self, article: Dict) -> None:
        execute_query(
            """
            INSERT OR IGNORE INTO news_articles(title, source, url, summary, category, published_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                article.get("title"),
                article.get("source"),
                article.get("url"),
                article.get("summary"),
                "crypto",
                article.get("published_at"),
            ),
        )

    @staticmethod
    def _entry_value(entry, key: str) -> str:
        if isinstance(entry, dict):
            value = entry.get(key, "")
        else:
            value = getattr(entry, key, "")
        if key == "content" and isinstance(value, list):
            return " ".join(str(item.get("value", item)) if isinstance(item, dict) else str(item) for item in value)
        return str(value or "")


news_service = NewsService()


def fetch_latest_news(query: str = "crypto", limit: int = 5) -> List[Dict]:
    return news_service.fetch_latest_news(query=query, limit=limit)


def fetch_from_rss(query: str = "crypto", limit: int = 5) -> List[Dict]:
    return news_service.fetch_from_rss(query=query, limit=limit)


def fetch_from_google(query: str = "crypto", limit: int = 5) -> List[Dict]:
    return news_service.fetch_from_google(query=query, limit=limit)


def clean_summary(summary: str, max_length: int = 240) -> str:
    return news_service.clean_summary(summary, max_length=max_length)


def summarize_news(articles: List[Dict]) -> str:
    return news_service.summarize_news(articles)


def save_article(article: Dict) -> None:
    news_service.save_article(article)
