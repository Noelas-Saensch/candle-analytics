import asyncio
import logging

from fastapi import APIRouter, Query

from candles.config import settings
from candles.fetcher import fetch_and_store, parse_pairs, parse_timeframes
from candles.storage.db import query_candles, get_available_pairs

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/candles")
async def get_candles(
    exchange: str | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    limit: int = Query(default=100),
    since: int | None = None,
    start_time: int | None = None,
    end_time: int | None = None,
):
    if limit < 1 or limit > 99999:
        limit = 99999
    rows = query_candles(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        since=since,
        start_time=start_time,
        end_time=end_time,
    )
    return {"count": len(rows), "candles": rows}


@router.get("/pairs")
async def list_pairs():
    return {"pairs": get_available_pairs()}


@router.post("/fetch")
async def api_fetch(
    exchange: str,
    symbol: str,
    timeframe: str,
    limit: int = Query(default=5000),
    start_time: int | None = None,
    end_time: int | None = None,
):
    result = await fetch_and_store(
        exchange_name=exchange,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
    )
    return result
