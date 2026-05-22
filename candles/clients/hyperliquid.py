import time

from candles.clients.base import BaseClient


HYPERLIQUID_BASE = "https://api.hyperliquid.xyz"

INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1H": "1h",
    "2H": "2h",
    "4H": "4h",
    "12H": "12h",
    "1D": "1d",
    "3D": "3d",
    "1W": "1w",
    "1M": "1M",
}

_INTERVAL_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1H": 3_600_000,
    "2H": 7_200_000,
    "4H": 14_400_000,
    "12H": 43_200_000,
    "1D": 86_400_000,
    "3D": 259_200_000,
    "1W": 604_800_000,
    "1M": 2_592_000_000,
}

_QUOTES = ("USDC", "USDT", "USD")


def _to_coin(symbol: str) -> str:
    for q in _QUOTES:
        if symbol.endswith(q) and len(symbol) > len(q):
            return symbol[: -len(q)]
    return symbol


class HyperliquidClient(BaseClient):
    def __init__(self):
        super().__init__(HYPERLIQUID_BASE, timeout=30.0)

    async def _post(self, body: dict) -> list | dict:
        resp = await self._http.post("/info", json=body)
        resp.raise_for_status()
        return resp.json()

    async def fetch_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 500,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict]:
        hl_interval = INTERVAL_MAP.get(interval)
        if hl_interval is None:
            supported = ", ".join(sorted(INTERVAL_MAP))
            raise ValueError(
                f"Unsupported Hyperliquid interval: {interval}. "
                f"Supported: {supported}"
            )

        coin = _to_coin(symbol)

        now_ms = int(time.time() * 1000)
        if end_time is None:
            end_time = now_ms
        if start_time is None:
            interval_ms = _INTERVAL_MS.get(interval, 3_600_000)
            start_time = end_time - (limit * interval_ms)

        body = {
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": hl_interval,
                "startTime": start_time,
                "endTime": end_time,
            },
        }

        raw = await self._post(body)

        return [
            {
                "timestamp": k["t"],
                "open": float(k["o"]),
                "high": float(k["h"]),
                "low": float(k["l"]),
                "close": float(k["c"]),
                "volume": float(k["v"]),
            }
            for k in raw
        ]

    async def fetch_5000_klines(
        self, symbol: str, interval: str = "1h"
    ) -> list[dict]:
        now_ms = int(time.time() * 1000)
        interval_ms = _INTERVAL_MS.get(interval, 3_600_000)
        start_time = now_ms - (5000 * interval_ms)
        return await self.fetch_klines(
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=now_ms,
        )
