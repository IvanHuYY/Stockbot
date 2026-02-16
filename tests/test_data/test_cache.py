"""Tests for TTL cache."""

import time

from stockbot.data.cache import TTLCache


def test_set_and_get():
    cache = TTLCache(default_ttl=60)
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"


def test_expired_entry():
    cache = TTLCache(default_ttl=1)
    cache.set("key1", "value1", ttl=0)
    time.sleep(0.1)
    assert cache.get("key1") is None


def test_invalidate():
    cache = TTLCache()
    cache.set("key1", "value1")
    cache.invalidate("key1")
    assert cache.get("key1") is None


def test_clear():
    cache = TTLCache()
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.clear()
    assert cache.get("key1") is None
    assert cache.get("key2") is None


def test_cleanup():
    cache = TTLCache()
    cache.set("key1", "value1", ttl=0)
    cache.set("key2", "value2", ttl=60)
    time.sleep(0.1)
    removed = cache.cleanup()
    assert removed == 1
    assert cache.get("key2") == "value2"
