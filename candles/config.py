from pathlib import Path
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    pairs: str = "binance:BTCUSDC binance:PAXGUSDC"
    timeframes: str = "1m 1H 1D"
    db_path: str = "data/candles.db"
    csv_dir: str = "data/csv"
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    class Config:
        env_file = PROJECT_ROOT / ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
