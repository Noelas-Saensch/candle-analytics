from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from api.dashboard import router as dashboard_router
from api.analyze import router as analyze_router
from candles.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("candle-analytics server starting")
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


@app.get("/api/health")
async def health():
    return {"status": "ok", "pairs": settings.pairs, "timeframes": settings.timeframes}
