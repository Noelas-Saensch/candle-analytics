from pathlib import Path
from candles.config import settings


def export_csv(candles: list[dict]) -> str | None:
    if not candles:
        return None
    ex = candles[0]["exchange"]
    sym = candles[0]["symbol"]
    tf = candles[0]["timeframe"]

    csv_dir = Path(settings.csv_dir)
    csv_dir.mkdir(parents=True, exist_ok=True)

    path = csv_dir / f"{ex}_{sym}_{tf}.csv"
    header = "timestamp,open,high,low,close,volume"
    rows = "\n".join(
        f"{c['timestamp']},{c['open']},{c['high']},{c['low']},{c['close']},{c['volume']}"
        for c in candles
    )
    path.write_text(header + "\n" + rows + "\n")
    return str(path)
