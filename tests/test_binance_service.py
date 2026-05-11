from services.binance_service import BinanceService


def test_normalize_symbol_adds_usdt_for_short_assets():
    service = BinanceService()
    assert service.normalize_symbol("btc") == "BTCUSDT"
    assert service.normalize_symbol("eth/usdt") == "ETHUSDT"
    assert service.normalize_symbol("SOL-USDT") == "SOLUSDT"


def test_normalize_symbol_keeps_full_pair():
    service = BinanceService()
    assert service.normalize_symbol("BTCUSDT") == "BTCUSDT"
