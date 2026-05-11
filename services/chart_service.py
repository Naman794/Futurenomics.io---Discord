from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd

from config import BASE_DIR


GENERATED_DIR = BASE_DIR / "charts" / "generated"


def _frame(klines: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(klines)
    df["date"] = pd.to_datetime(df["open_time"], unit="ms")
    return df.set_index("date")


def _filename(symbol: str, kind: str) -> Path:
    safe = "".join(char for char in symbol.upper() if char.isalnum())
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    return GENERATED_DIR / f"{safe}_{kind}_{stamp}.png"


def create_line_chart(symbol: str, klines: list[dict]) -> str:
    df = _frame(klines)
    path = _filename(symbol, "line")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df.index, df["close"], label="Close")
    ax.set_title(f"{symbol.upper()} Close Price")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def create_candlestick_chart(symbol: str, klines: list[dict]) -> str:
    df = _frame(klines)[["open", "high", "low", "close", "volume"]]
    df.columns = ["Open", "High", "Low", "Close", "Volume"]
    path = _filename(symbol, "candlestick")
    mpf.plot(df, type="candle", volume=True, title=f"{symbol.upper()} Candles", style="yahoo", savefig=str(path))
    return str(path)


def create_volume_chart(symbol: str, klines: list[dict]) -> str:
    df = _frame(klines)
    path = _filename(symbol, "volume")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(df.index, df["volume"], label="Volume")
    ax.set_title(f"{symbol.upper()} Volume")
    ax.set_xlabel("Time")
    ax.set_ylabel("Volume")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)
