import logging

from candles.config import settings
from candles.models import PairConfig
from candles.clients.binance import BinanceClient
from candles.clients.hyperliquid import HyperliquidClient
from candles.storage.db import save_candles
from candles.storage.csv_writer import export_csv

logger = logging.getLogger(__name__)

CLIENTS = {
    "binance": BinanceClient,
    "hyperliquid": HyperliquidClient,
}


def parse_pairs(raw: str) -> list[PairConfig]:
    pairs = []
    for token in raw.strip().split():
        if ":" not in token:
            continue
        parts = token.split(":", 1)
        pairs.append(PairConfig(exchange=parts[0], symbol=parts[1]))
    return pairs


def parse_timeframes(raw: str) -> list[str]:
    return raw.strip().split()


async def fetch_and_store(
    exchange_name: str,
    symbol: str,
    timeframe: str,
    limit: int = 500,
    start_time: int | None = None,
    end_time: int | None = None,
) -> dict:
    client_cls = CLIENTS.get(exchange_name)
    if client_cls is None:
        return {"status": "skipped", "reason": f"unknown exchange: {exchange_name}"}

    client = client_cls()
    try:
        raw = await client.fetch_klines(
            symbol=symbol,
            interval=timeframe,
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )
    except NotImplementedError as e:
        return {"status": "skipped", "reason": str(e)}
    except Exception as e:
        logger.exception("fetch failed: %s:%s %s", exchange_name, symbol, timeframe)
        return {"status": "error", "reason": str(e)}
    finally:
        await client.close()

    candles = [
        {
            "exchange": exchange_name,
            "symbol": symbol,
            "timeframe": timeframe,
            **k,
        }
        for k in raw
    ]

    stored = save_candles(candles)
    csv_path = export_csv(candles)

    return {
        "status": "ok",
        "exchange": exchange_name,
        "symbol": symbol,
        "timeframe": timeframe,
        "count": stored,
        "csv": csv_path,
    }


async def fetch_all_pairs(
    timeframes: list[str] | None = None,
    limit: int = 500,
    start_time: int | None = None,
    end_time: int | None = None,
) -> list[dict]:
    pairs = parse_pairs(settings.pairs)
    tfs = timeframes or parse_timeframes(settings.timeframes)
    results = []

    for pair in pairs:
        for tf in tfs:
            result = await fetch_and_store(
                pair.exchange, pair.symbol, tf, limit, start_time, end_time
            )
            results.append(result)
            logger.info(
                "%s:%s %s → %s (%d candles)",
                pair.exchange, pair.symbol, tf,
                result["status"], result.get("count", 0),
            )

    return results
