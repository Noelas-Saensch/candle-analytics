import argparse
import asyncio
import logging

from candles.fetcher import fetch_all_pairs
from candles.storage.db import query_candles, get_available_pairs

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def cmd_fetch(args):
    results = await fetch_all_pairs(
        timeframes=args.timeframes.split() if args.timeframes else None,
        limit=args.limit,
    )
    ok = sum(1 for r in results if r["status"] == "ok")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors = sum(1 for r in results if r["status"] == "error")
    print(f"Done: {ok} ok, {skipped} skipped, {errors} errors")


def cmd_list(args):
    pairs = get_available_pairs()
    if not pairs:
        print("No data stored yet.")
        return
    for p in pairs:
        print(f"{p['exchange']}:{p['symbol']} [{p['timeframe']}]")


def cmd_query(args):
    rows = query_candles(
        exchange=args.exchange,
        symbol=args.symbol,
        timeframe=args.timeframe,
        limit=args.limit,
    )
    print(f"{'timestamp':<18} {'open':>12} {'high':>12} {'low':>12} {'close':>12} {'vol':>12}")
    for r in rows:
        print(f"{r['timestamp']:<18} {r['open']:>12.4f} {r['high']:>12.4f} {r['low']:>12.4f} {r['close']:>12.4f} {r['volume']:>12.2f}")


def cmd_server(args):
    import uvicorn
    from api.main import app
    uvicorn.run(app, host=args.host, port=args.port)


def main():
    parser = argparse.ArgumentParser(prog="candle-analytics")
    sub = parser.add_subparsers(dest="command")

    fetch_p = sub.add_parser("fetch", help="Fetch latest candles")
    fetch_p.add_argument("--timeframes", help="Override timeframes (space-separated)")
    fetch_p.add_argument("--limit", type=int, default=500)
    fetch_p.set_defaults(func=cmd_fetch)

    sub.add_parser("list", help="List stored pairs").set_defaults(func=cmd_list)

    query_p = sub.add_parser("query", help="Query stored candles")
    query_p.add_argument("--exchange")
    query_p.add_argument("--symbol")
    query_p.add_argument("--timeframe")
    query_p.add_argument("--limit", type=int, default=100)
    query_p.set_defaults(func=cmd_query)

    server_p = sub.add_parser("server", help="Start FastAPI server")
    server_p.add_argument("--host", default=None)
    server_p.add_argument("--port", type=int, default=None)
    server_p.set_defaults(func=cmd_server)

    args = parser.parse_args()
    if args.command:
        asyncio.run(args.func(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
