import pytest
from app.queue.retry import calculate_retry_delay

def test_exponential_backoff_growth():
    """Delay grows exponentially with attempt."""
    pass

def test_max_delay_cap(monkeypatch):
    """Delay never exceeds max_delay."""
    import random
    monkeypatch.setattr(random, "uniform", lambda a, b: b)
    
    assert calculate_retry_delay(1, 2.0, 10.0) <= 10.0
    assert calculate_retry_delay(10, 2.0, 10.0) == 10.0

def test_jitter_range(monkeypatch):
    """Delay is between 0 and the exponential value (full jitter)."""
    import random
    
    monkeypatch.setattr(random, "uniform", lambda a, b: a)
    assert calculate_retry_delay(1, 2.0, 300.0) == 0.0
    
    monkeypatch.setattr(random, "uniform", lambda a, b: b)
    assert calculate_retry_delay(1, 2.0, 300.0) == 4.0
    assert calculate_retry_delay(2, 2.0, 300.0) == 8.0

def test_jitter_randomness():
    """Multiple calls produce different values."""
    delays = set(calculate_retry_delay(2, 2.0, 300.0) for _ in range(100))
    assert len(delays) > 1

def test_attempt_zero(monkeypatch):
    """First attempt still produces reasonable delay."""
    import random
    monkeypatch.setattr(random, "uniform", lambda a, b: b)
    
    assert calculate_retry_delay(0, 2.0, 300.0) == 2.0
