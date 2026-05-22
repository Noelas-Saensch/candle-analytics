import sqlite3
from pathlib import Path
from candles.config import settings


def _get_connection() -> sqlite3.Connection:
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            exchange TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            PRIMARY KEY (exchange, symbol, timeframe, timestamp)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ohlcv_lookup
        ON ohlcv(exchange, symbol, timeframe, timestamp)
    """)
    conn.commit()
    return conn


def save_candles(candles: list[dict]) -> int:
    conn = _get_connection()
    try:
        count = 0
        for c in candles:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO ohlcv
                    (exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    c["exchange"], c["symbol"], c["timeframe"],
                    c["timestamp"], c["open"], c["high"],
                    c["low"], c["close"], c["volume"],
                ))
                count += 1
            except Exception:
                pass
        conn.commit()
        return count
    finally:
        conn.close()


def query_candles(
    exchange: str | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    limit: int = 1000,
    since: int | None = None,
    start_time: int | None = None,
    end_time: int | None = None,
) -> list[dict]:
    conn = _get_connection()
    try:
        conditions = []
        params = []
        if exchange:
            conditions.append("exchange = ?")
            params.append(exchange)
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        if timeframe:
            conditions.append("timeframe = ?")
            params.append(timeframe)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)

        where = " AND ".join(conditions) if conditions else "1"
        cursor = conn.execute(
            f"SELECT * FROM ohlcv WHERE {where} ORDER BY timestamp ASC LIMIT ?",
            params + [limit],
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_available_pairs() -> list[dict]:
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT DISTINCT exchange, symbol, timeframe FROM ohlcv ORDER BY exchange, symbol, timeframe"
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
