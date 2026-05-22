from pydantic import BaseModel


class OHLCV(BaseModel):
    exchange: str
    symbol: str
    timeframe: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    def to_csv_row(self) -> list:
        return [self.timestamp, self.open, self.high, self.low, self.close, self.volume]

    @classmethod
    def csv_header(cls) -> list[str]:
        return ["timestamp", "open", "high", "low", "close", "volume"]


class PairConfig(BaseModel):
    exchange: str
    symbol: str

    @property
    def key(self) -> str:
        return f"{self.exchange}:{self.symbol}"


SUPPORTED_TIMEFRAMES = [
    "1m", "5m", "15m", "30m",
    "1H", "2H", "4H", "6H", "12H",
    "1D", "2D", "3D",
    "1W", "2W",
    "1M", "2M", "3M", "4M", "6M",
    "1Y",
]

DEFAULT_TIMEFRAMES = ["1m", "1H", "1D"]
