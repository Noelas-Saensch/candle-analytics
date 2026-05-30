from contextlib import asynccontextmanager
import logging
from dotenv import load_dotenv

load_dotenv(dotenv_path="/home/anymous/PROJETS/candle-analytics/.env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from api.dashboard import router as dashboard_router
from api.analyze import router as analyze_router
from api.strategy_lab import router as strategy_lab_router
from api.vibe_lab import router as vibe_lab_router
from api.convert import router as convert_router
from candles.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("candle-analytics server starting")
    from candles.storage.db import backfill_metrics
    n = backfill_metrics()
    if n:
        logger.info("backfilled %d rows with pre-computed metrics", n)
    yield
    logger.info("candle-analytics server stopped")


app = FastAPI(
    title="Candle Analytics API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(dashboard_router)
app.include_router(analyze_router)
app.include_router(strategy_lab_router)
app.include_router(vibe_lab_router)
app.include_router(convert_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "pairs": settings.pairs, "timeframes": settings.timeframes}
