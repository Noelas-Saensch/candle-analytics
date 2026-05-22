import time

from candles.clients.base import BaseClient


BINANCE_BASE = "https://api.binance.com"
BINANCE_MAX_LIMIT = 1000

INTERVAL_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1H": "1h", "2H": "2h", "4H": "4h", "6H": "6h", "12H": "12h",
    "1D": "1d", "2D": "2d", "3D": "3d",
    "1W": "1w", "2W": "2w",
    "1M": "1M", "2M": "2M", "3M": "3M", "4M": "4M", "6M": "6M",
    "1Y": "1M",
}

_INTERVAL_MS = {
    "1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1H": 3_600_000, "2H": 7_200_000, "4H": 14_400_000, "6H": 21_600_000,
    "12H": 43_200_000, "1D": 86_400_000, "2D": 172_800_000, "3D": 259_200_000,
    "1W": 604_800_000, "2W": 1_209_600_000,
    "1M": 2_592_000_000, "2M": 5_184_000_000, "3M": 7_776_000_000,
    "4M": 10_368_000_000, "6M": 15_552_000_000,
}


def _parse_klines(raw: list) -> list[dict]:
    return [
        {
            "timestamp": k[0],
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        }
        for k in raw
    ]


class BinanceClient(BaseClient):
    def __init__(self):
        super().__init__(BINANCE_BASE)

    async def fetch_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 500,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict]:
        binance_interval = INTERVAL_MAP.get(interval)
        if binance_interval is None:
            raise ValueError(f"Unsupported Binance interval: {interval}")

        params = {
            "symbol": symbol,
            "interval": binance_interval,
            "limit": min(limit, BINANCE_MAX_LIMIT),
        }
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        raw = await self._get("/api/v3/klines", params=params)
        all_candles = _parse_klines(raw)

        # Paginate backwards when limit > 1000
        if limit > BINANCE_MAX_LIMIT and len(all_candles) == BINANCE_MAX_LIMIT:
            interval_ms = _INTERVAL_MS.get(interval, 3_600_000)
            while len(all_candles) < limit:
                next_end = all_candles[0]["timestamp"] - interval_ms
                if start_time and next_end < start_time:
                    break
                params["endTime"] = next_end
                params.pop("startTime", None)
                params["limit"] = BINANCE_MAX_LIMIT
                raw = await self._get("/api/v3/klines", params=params)
                batch = _parse_klines(raw)
                if not batch:
                    break
                all_candles = batch + all_candles
                if len(batch) < BINANCE_MAX_LIMIT:
                    break

        return all_candles[:limit]

    async def fetch_5000_klines(
        self, symbol: str, interval: str = "1h"
    ) -> list[dict]:
        return await self.fetch_klines(symbol, interval, limit=5000)
