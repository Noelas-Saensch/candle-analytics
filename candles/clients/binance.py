from candles.clients.base import BaseClient


BINANCE_BASE = "https://api.binance.com"

INTERVAL_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1H": "1h", "2H": "2h", "4H": "4h", "6H": "6h", "12H": "12h",
    "1D": "1d", "2D": "2d", "3D": "3d",
    "1W": "1w", "2W": "2w",
    "1M": "1M", "2M": "2M", "3M": "3M", "4M": "4M", "6M": "6M",
    "1Y": "1M",
}


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

        params = {"symbol": symbol, "interval": binance_interval, "limit": limit}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        raw = await self._get("/api/v3/klines", params=params)

        result = []
        for k in raw:
            result.append({
                "timestamp": k[0],
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            })
        return result

    async def fetch_5000_klines(
        self, symbol: str, interval: str = "1h"
    ) -> list[dict]:
        interval_ms = {
            "1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
            "1H": 3_600_000, "2H": 7_200_000, "4H": 14_400_000, "6H": 21_600_000,
            "12H": 43_200_000, "1D": 86_400_000, "2D": 172_800_000, "3D": 259_200_000,
            "1W": 604_800_000, "2W": 1_209_600_000,
        }.get(interval, 3_600_000)

        total_bars = 5000
        all_candles = []
        import time
        end_time = int(time.time() * 1000)

        while len(all_candles) < total_bars:
            batch = await self.fetch_klines(
                symbol, interval, limit=1000, end_time=end_time
            )
            if not batch:
                break
            all_candles = batch + all_candles
            if len(batch) < 1000:
                break
            end_time = batch[0]["timestamp"] - interval_ms

        return all_candles[-total_bars:]
