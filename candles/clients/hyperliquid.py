from candles.clients.base import BaseClient


HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"


class HyperliquidClient(BaseClient):
    def __init__(self):
        super().__init__(HYPERLIQUID_INFO_URL, timeout=30.0)

    async def fetch_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 500,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict]:
        raise NotImplementedError(
            "Hyperliquid OHLCV endpoint TBD. "
            "See https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint"
        )

    async def fetch_5000_klines(
        self, symbol: str, interval: str = "1h"
    ) -> list[dict]:
        raise NotImplementedError("Hyperliquid backfill TBD")
