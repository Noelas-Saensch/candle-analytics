import asyncio
import json
import logging
from abc import ABC, abstractmethod

from candles.clients.binance import INTERVAL_MAP as BINANCE_INTERVAL_MAP
from candles.clients.hyperliquid import INTERVAL_MAP as HL_INTERVAL_MAP, _to_coin
from candles.storage.db import save_candles

logger = logging.getLogger(__name__)


def _parse_binance_symbol(symbol: str) -> str:
    return symbol.lower()


def _candle_to_row(exchange: str, symbol: str, timeframe: str, c: dict) -> dict:
    return {
        "exchange": exchange,
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": c["timestamp"],
        "open": float(c["open"]),
        "high": float(c["high"]),
        "low": float(c["low"]),
        "close": float(c["close"]),
        "volume": float(c["volume"]),
    }


class BaseHandler(ABC):
    def __init__(self, exchange: str):
        self.exchange = exchange
        self._running = False

    @abstractmethod
    async def run(self): ...

    async def stop(self):
        self._running = False


class BinanceHandler(BaseHandler):
    WS_BASE = "wss://stream.binance.com:9443/stream"

    def __init__(self, pairs: list[dict]):
        super().__init__("binance")
        self.pairs = pairs

    async def run(self):
        import websockets

        streams = []
        for p in self.pairs:
            sym = _parse_binance_symbol(p["symbol"])
            tf = BINANCE_INTERVAL_MAP.get(p["timeframe"])
            if tf:
                streams.append(f"{sym}@kline_{tf}")

        if not streams:
            logger.warning("binance: no valid streams to subscribe")
            return

        url = f"{self.WS_BASE}?streams={'/'.join(streams)}"
        self._running = True

        while self._running:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    logger.info("binance stream connected (%d streams)", len(streams))
                    async for raw in ws:
                        if not self._running:
                            break
                        await self._on_message(raw)
            except Exception as e:
                if self._running:
                    logger.warning("binance stream disconnected: %s — reconnecting in 5s", e)
                    await asyncio.sleep(5)

    async def _on_message(self, raw: str):
        try:
            msg = json.loads(raw)
            data = msg.get("data", {})
            if data.get("e") != "kline":
                return
            k = data.get("k", {})
            if not k:
                return
            candle = {
                "timestamp": k["t"],
                "open": k["o"],
                "high": k["h"],
                "low": k["l"],
                "close": k["c"],
                "volume": k["v"],
            }
            row = _candle_to_row(
                "binance",
                data["s"],
                self._find_timeframe(data["s"], k["i"]),
                candle,
            )
            if row:
                save_candles([row])
        except Exception:
            logger.exception("binance: failed to process message")

    def _find_timeframe(self, symbol: str, binance_interval: str) -> str:
        for our_tf, bin_tf in BINANCE_INTERVAL_MAP.items():
            if bin_tf == binance_interval:
                return our_tf
        return binance_interval


class HyperliquidHandler(BaseHandler):
    WS_URL = "wss://api.hyperliquid.xyz/ws"

    def __init__(self, pairs: list[dict]):
        super().__init__("hyperliquid")
        self.pairs = pairs

    async def run(self):
        import websockets

        self._running = True

        while self._running:
            try:
                async with websockets.connect(self.WS_URL, ping_interval=20) as ws:
                    logger.info("hyperliquid stream connected (%d streams)", len(self.pairs))
                    for p in self.pairs:
                        coin = _to_coin(p["symbol"])
                        hl_interval = HL_INTERVAL_MAP.get(p["timeframe"])
                        if not hl_interval:
                            continue
                        sub = json.dumps({
                            "method": "subscribe",
                            "subscription": {
                                "type": "candle",
                                "coin": coin,
                                "interval": hl_interval,
                            },
                        })
                        await ws.send(sub)
                    async for raw in ws:
                        if not self._running:
                            break
                        await self._on_message(raw)
            except Exception as e:
                if self._running:
                    logger.warning("hyperliquid stream disconnected: %s — reconnecting in 5s", e)
                    await asyncio.sleep(5)

    async def _on_message(self, raw: str):
        try:
            msg = json.loads(raw)
            if msg.get("channel") != "candle":
                return
            data = msg.get("data", {})
            if not data:
                return
            coin = data.get("s", "")
            candle = {
                "timestamp": data["t"],
                "open": data["o"],
                "high": data["h"],
                "low": data["l"],
                "close": data["c"],
                "volume": data["v"],
            }
            row = _candle_to_row(
                "hyperliquid",
                self._find_symbol(coin),
                self._find_timeframe(data.get("i", "")),
                candle,
            )
            if row:
                save_candles([row])
        except Exception:
            logger.exception("hyperliquid: failed to process message")

    def _find_symbol(self, coin: str) -> str:
        for p in self.pairs:
            if _to_coin(p["symbol"]) == coin:
                return p["symbol"]
        return coin

    def _find_timeframe(self, hl_interval: str) -> str:
        for our_tf, hl_tf in HL_INTERVAL_MAP.items():
            if hl_tf == hl_interval:
                return our_tf
        return hl_interval
