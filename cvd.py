import json
import urllib.request
from datetime import datetime, timezone

symbols = ["BTCUSDT", "ETHUSDT"]
results = {}

for symbol in symbols:
    url = (
        "https://data-api.binance.vision/api/v3/aggTrades"
        f"?symbol={symbol}&limit=1000"
    )
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "CVD-Collector/1.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            trades = json.load(response)

        buy = sum(float(t["q"]) for t in trades if not t["m"])
        sell = sum(float(t["q"]) for t in trades if t["m"])

        results[symbol] = {
            "buy_volume": round(buy, 6),
            "sell_volume": round(sell, 6),
            "cvd": round(buy - sell, 6),
            "trade_count": len(trades),
            "first_trade_ms": trades[0]["T"],
            "last_trade_ms": trades[-1]["T"]
        }
    except Exception as e:
        results[symbol] = {"error": str(e)}

output = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "note": "Latest 1000 aggregate trades only; not 1h or 4h CVD",
    "results": results
}

with open("cvd_latest.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(json.dumps(output, ensure_ascii=False, indent=2))
