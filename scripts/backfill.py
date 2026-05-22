#!/usr/bin/env python3
"""
Backfill: fetch last 5000 candles for each default timeframe (1m, 1H, 1D)
for all configured pairs.

Usage:
    python scripts/backfill.py
    python scripts/backfill.py --timeframes "1H 1D"
"""
import argparse
import asyncio
import logging

from candles.fetcher import fetch_all_pairs, parse_pairs, parse_timeframes

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Backfill 5000 candles")
    parser.add_argument("--timeframes", default=None, help="Override timeframes")
    args = parser.parse_args()

    tfs = parse_timeframes(args.timeframes) if args.timeframes else parse_timeframes("1m 1H 1D")
    print(f"Backfilling last 5000 bars for timeframes: {tfs}")
    print()

    results = await fetch_all_pairs(timeframes=tfs, limit=5000)

    ok = sum(1 for r in results if r["status"] == "ok")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors = sum(1 for r in results if r["status"] == "error")

    print()
    print(f"Backfill complete: {ok} ok, {skipped} skipped, {errors} errors")
    if errors:
        print("Errors:")
        for r in results:
            if r["status"] == "error":
                print(f"  {r.get('exchange','?')}:{r.get('symbol','?')} [{r.get('timeframe','?')}] → {r['reason']}")


if __name__ == "__main__":
    asyncio.run(main())
