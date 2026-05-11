from datetime import datetime

from database.db import execute_query, fetch_all
from services.binance_service import binance_service


def create_alert(user_id: str, symbol: str, condition_type: str, target_price: float) -> int:
    normalized = binance_service.normalize_symbol(symbol)
    return execute_query(
        """
        INSERT INTO user_alerts(discord_user_id, symbol, condition_type, target_price)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, normalized, condition_type.lower(), target_price),
    )


def get_user_alerts(user_id: str) -> list[dict]:
    return fetch_all(
        "SELECT * FROM user_alerts WHERE discord_user_id = ? AND is_active = 1 ORDER BY created_at DESC",
        (user_id,),
    )


def delete_alert(alert_id: int, user_id: str) -> bool:
    row_id = execute_query(
        "UPDATE user_alerts SET is_active = 0 WHERE id = ? AND discord_user_id = ?",
        (alert_id, user_id),
    )
    return row_id >= 0


def should_trigger(condition_type: str, current_price: float, target_price: float) -> bool:
    if condition_type == "above":
        return current_price >= target_price
    if condition_type == "below":
        return current_price <= target_price
    return False


async def check_active_alerts() -> list[dict]:
    alerts = fetch_all("SELECT * FROM user_alerts WHERE is_active = 1")
    triggered: list[dict] = []
    price_cache: dict[str, float] = {}
    for alert in alerts:
        symbol = alert["symbol"]
        if symbol not in price_cache:
            price_cache[symbol] = (await binance_service.get_price(symbol))["price"]
        current_price = price_cache[symbol]
        if should_trigger(alert["condition_type"], current_price, float(alert["target_price"])):
            deactivate_alert(alert["id"])
            triggered.append({**alert, "current_price": current_price})
    return triggered


def deactivate_alert(alert_id: int) -> None:
    execute_query(
        "UPDATE user_alerts SET is_active = 0, triggered_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), alert_id),
    )
