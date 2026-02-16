"""Sentiment analysis tools for news articles."""

from __future__ import annotations

import json

from langchain_core.tools import tool


@tool
def analyze_news_sentiment(articles_json: str) -> str:
    """Analyze sentiment of news articles for a stock.
    Input: JSON array of objects with 'title' and 'summary' fields.
    Returns aggregate sentiment score and per-article breakdown."""
    articles = json.loads(articles_json)

    if not articles:
        return json.dumps({
            "overall_sentiment": 0.0,
            "sentiment_label": "neutral",
            "article_count": 0,
            "details": [],
        })

    # Keyword-based sentiment scoring as a fast baseline
    # (In production, this would use the LLM or a fine-tuned model)
    positive_words = {
        "surge", "soar", "rally", "gain", "beat", "exceed", "upgrade",
        "bullish", "record", "growth", "profit", "strong", "outperform",
        "breakthrough", "innovation", "partnership", "expand", "revenue",
        "positive", "optimistic", "buy", "overweight",
    }
    negative_words = {
        "crash", "plunge", "fall", "drop", "miss", "downgrade", "bearish",
        "loss", "weak", "decline", "lawsuit", "investigation", "recall",
        "debt", "default", "negative", "pessimistic", "sell", "underweight",
        "layoff", "cut", "warning", "risk", "concern",
    }

    details = []
    total_score = 0.0

    for article in articles:
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        words = set(text.split())

        pos_count = len(words & positive_words)
        neg_count = len(words & negative_words)
        total = pos_count + neg_count

        if total == 0:
            score = 0.0
        else:
            score = (pos_count - neg_count) / total

        score = max(-1.0, min(1.0, score))
        total_score += score

        details.append({
            "title": article.get("title", ""),
            "sentiment_score": round(score, 2),
        })

    avg_score = total_score / len(articles) if articles else 0.0

    if avg_score > 0.3:
        label = "positive"
    elif avg_score < -0.3:
        label = "negative"
    else:
        label = "neutral"

    return json.dumps({
        "overall_sentiment": round(avg_score, 2),
        "sentiment_label": label,
        "article_count": len(articles),
        "details": details,
    })
