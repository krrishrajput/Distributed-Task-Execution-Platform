import random

def calculate_retry_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    """Exponential backoff with full jitter."""
    delay = min(max_delay, base_delay * (2 ** attempt))
    return random.uniform(0, delay)
