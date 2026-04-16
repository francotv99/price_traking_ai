"""Tests for RAG corpus chunking utilities."""

from rag.corpus import CorpusBuilder


def test_chunk_text_splits_long_input() -> None:
    builder = CorpusBuilder(chunk_size=50, overlap=10)
    text = "a" * 140

    chunks = builder._chunk_text(text)

    assert len(chunks) >= 3
    assert all(len(c) <= 50 for c in chunks)


def test_extract_sections_contains_expected_keys() -> None:
    builder = CorpusBuilder()
    payload = {
        "description": {"en": "<p>Bitcoin description</p>"},
        "market_data": {
            "current_price": {"usd": 100.0},
            "market_cap": {"usd": 1000.0},
            "total_volume": {"usd": 10.0},
            "ath": {"usd": 200.0},
        },
        "community_data": {
            "reddit_subscribers": 123,
            "twitter_followers": 456,
        },
        "links": {
            "homepage": ["https://bitcoin.org"],
            "subreddit_url": "https://reddit.com/r/bitcoin",
        },
    }

    sections = builder._extract_sections("bitcoin", payload)

    assert set(sections.keys()) == {"description", "market_data", "community", "links"}
    assert "Bitcoin description" in sections["description"]
