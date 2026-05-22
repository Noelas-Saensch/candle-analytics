import asyncio
import logging
import signal

from candles.config import settings
from candles.fetcher import parse_pairs, parse_timeframes
from candles.stream.handler import BinanceHandler, HyperliquidHandler

logger = logging.getLogger(__name__)


def _group_pairs(pairs: list, exchange: str) -> list[dict]:
    return [
        {"symbol": p.symbol, "timeframe": tf}
        for p in pairs
        if p.exchange == exchange
        for tf in (parse_timeframes(settings.timeframes) or ["1m"])
    ]


async def run_stream():
    pairs = parse_pairs(settings.pairs)
    handlers = []

    binance_pairs = _group_pairs(pairs, "binance")
    hyperliquid_pairs = _group_pairs(pairs, "hyperliquid")

    if binance_pairs:
        handlers.append(BinanceHandler(binance_pairs))
    if hyperliquid_pairs:
        handlers.append(HyperliquidHandler(hyperliquid_pairs))

    if not handlers:
        logger.warning("no handlers configured")
        return

    stop_event = asyncio.Event()

    def _signal():
        logger.info("shutdown requested — stopping streams...")
        for h in handlers:
            h._running = False
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal)

    tasks = [asyncio.create_task(h.run()) for h in handlers]

    logger.info("stream running — press Ctrl+C to stop")
    await stop_event.wait()

    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("all streams stopped")
