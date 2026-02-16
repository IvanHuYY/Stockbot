"""News data fetching and sentiment analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

import structlog
from alpaca.data.requests import NewsRequest

if TYPE_CHECKING:
    from alpaca.data.historical.news import NewsClient

logger = structlog.get_logger()


@dataclass
class NewsArticle:
    title: str
    summary: str
    source: str
    url: str
    published_at: datetime
    symbols: list[str] = field(default_factory=list)
    sentiment_score: float | None = None


class NewsService:
    """Fetch news from Alpaca and score sentiment."""

    def __init__(self, api_key: str, secret_key: str) -> None:
        from alpaca.data.historical.news import NewsClient

        self._client = NewsClient(api_key=api_key, secret_key=secret_key)

    def get_news(
        self,
        symbols: list[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> list[NewsArticle]:
        """Fetch recent news articles."""
        request = NewsRequest(
            symbols=symbols,
            start=start,
            end=end,
            limit=limit,
        )
        news = self._client.get_news(request)

        articles = []
        for item in news.news:
            articles.append(
                NewsArticle(
                    title=item.headline,
                    summary=item.summary or "",
                    source=item.source,
                    url=item.url,
                    published_at=item.created_at,
                    symbols=[s for s in (item.symbols or [])],
                )
            )

        logger.debug("Fetched news", count=len(articles), symbols=symbols)
        return articles

    def get_news_for_symbol(self, symbol: str, limit: int = 10) -> list[NewsArticle]:
        """Fetch news for a specific symbol."""
        return self.get_news(symbols=[symbol], limit=limit)
