def format_price(value: float | None) -> str:
    if value is None:
        return "N/A"
    if value >= 1:
        return f"${value:,.2f}"
    return f"${value:,.8f}".rstrip("0").rstrip(".")


def format_percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def format_volume(value: float | None) -> str:
    if value is None:
        return "N/A"
    for suffix in ("", "K", "M", "B", "T"):
        if abs(value) < 1000:
            return f"{value:,.2f}{suffix}"
        value /= 1000
    return f"{value:,.2f}Q"


def truncate_text(text: str, limit: int = 1024) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."
