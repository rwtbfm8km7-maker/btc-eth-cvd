import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

BASE = "https://data-api.binance.vision/api/v3/aggTrades"
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
HOURS = [1, 4]


def get_trades(symbol, start_ms, end_ms):
    all_trades = []
    next_id = None

    while True:
        params = {"symbol": symbol, "limit": 1000}
        if next_id is None:
            params["startTime"] = start_ms
            params["endTime"] = end_ms - 1
        else:
            params["fromId"] = next_id

        url = BASE + "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(
            url, headers={"User-Agent": "CVD-Collector/2.0"}
        )

        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=25) as response:
                    batch = json.load(response)
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)

        if not batch:
            break

        selected = [
            t for t in batch
            if start_ms <= int(t["T"]) < end_ms
        ]
        all_trades.extend(selected)

        if len(batch) < 1000 or int(batch[-1]["T"]) >= end_ms:
            break

        new_id = int(batch[-1]["a"]) + 1
        if next_id is not None and new_id <= next_id:
            raise RuntimeError("Pagination did not advance")
        next_id = new_id
        time.sleep(0.15)

        if len(all_trades) > 1000000:
            raise RuntimeError("Trade safety limit exceeded")

    if not all_trades:
        raise RuntimeError("No trades returned")

    if int(all_trades[0]["T"]) > start_ms + 60000:
        raise RuntimeError("Beginning of interval not verified")

    if int(all_trades[-1]["T"]) < end_ms - 60000:
        raise RuntimeError("End of interval not verified")

    return all_trades


def calculate(trades):
    buy = sum(float(t["q"]) for t in trades if not t["m"])
    sell = sum(float(t["q"]) for t in trades if t["m"])
    return {
        "buy_volume": round(buy, 6),
        "sell_volume": round(sell, 6),
        "cvd": round(buy - sell, 6),
        "trade_count": len(trades)
    }


now_ms = int(time.time() * 1000)
end_ms = (now_ms // 3600000) * 3600000

output = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "source": "Binance spot aggregate trades",
    "note": "Completed UTC hourly windows; errors must not be used as CVD",
    "results": {}
}

for symbol in SYMBOLS:
    output["results"][symbol] = {}
    for hours in HOURS:
        start_ms = end_ms - hours * 3600000
        key = f"{hours}h"
        try:
            trades = get_trades(symbol, start_ms, end_ms)
            result = calculate(trades)
            result["start_utc"] = datetime.fromtimestamp(
                start_ms / 1000, timezone.utc
            ).isoformat()
            result["end_utc"] = datetime.fromtimestamp(
                end_ms / 1000, timezone.utc
            ).isoformat()
            result["status"] = "ok"
        except Exception as exc:
            result = {
                "status": "error",
                "error": str(exc)
            }
        output["results"][symbol][key] = result

with open("cvd_latest.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(json.dumps(output, ensure_ascii=False, indent=2))
