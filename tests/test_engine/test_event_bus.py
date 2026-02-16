"""Tests for the event bus."""

from stockbot.engine.event_bus import EventBus


def test_publish_subscribe():
    bus = EventBus()
    received = []

    bus.subscribe("test_event", lambda data: received.append(data))
    bus.publish("test_event", {"value": 42})

    assert len(received) == 1
    assert received[0]["value"] == 42


def test_multiple_subscribers():
    bus = EventBus()
    results = []

    bus.subscribe("event", lambda d: results.append("handler1"))
    bus.subscribe("event", lambda d: results.append("handler2"))
    bus.publish("event")

    assert len(results) == 2


def test_unsubscribe():
    bus = EventBus()
    received = []
    handler = lambda d: received.append(d)

    bus.subscribe("event", handler)
    bus.unsubscribe("event", handler)
    bus.publish("event", "data")

    assert len(received) == 0


def test_clear():
    bus = EventBus()
    bus.subscribe("event1", lambda d: None)
    bus.subscribe("event2", lambda d: None)
    bus.clear()

    # Should not raise
    bus.publish("event1")
    bus.publish("event2")
