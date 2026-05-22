from fastapi import APIRouter, Query

from candles.storage.db import query_candles, get_available_pairs

router = APIRouter()


@router.get("/candles")
async def get_candles(
    exchange: str | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    limit: int = Query(default=100, le=5000),
    since: int | None = None,
):
    rows = query_candles(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        since=since,
    )
    return {"count": len(rows), "candles": rows}


@router.get("/pairs")
async def list_pairs():
    return {"pairs": get_available_pairs()}
