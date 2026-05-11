from typing import Iterable


SUPPORTED_INTERVALS = {"1m", "5m", "15m", "1h", "4h", "1d"}
SUPPORTED_ALERT_CONDITIONS = {"above", "below"}


def validate_crypto_symbol(symbol: str) -> bool:
    cleaned = symbol.strip().upper()
    return cleaned.isalnum() and 5 <= len(cleaned) <= 20


def validate_interval(interval: str, allowed: Iterable[str] = SUPPORTED_INTERVALS) -> bool:
    return interval in set(allowed)


def validate_alert_condition(condition: str) -> bool:
    return condition.lower() in SUPPORTED_ALERT_CONDITIONS


def validate_price(price: float) -> bool:
    return price > 0
