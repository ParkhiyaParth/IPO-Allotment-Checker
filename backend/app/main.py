import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_allotment, routes_device_pans, routes_ipos, routes_push
from app.config import settings
from app.services import ipo_catalog_service, ipo_list_service
from app.utils.http_client import close_http_client

# Without this, INFO-level logger.info() calls anywhere in the app are
# silently dropped — Python's logging module only auto-installs a fallback
# handler for WARNING+, and uvicorn's own logging setup only configures its
# own named loggers (uvicorn/uvicorn.access/uvicorn.error), never the root
# logger our app's loggers propagate up to. Confirmed the hard way: several
# logger.info() calls (including the /diagnostics endpoint) were reaching
# this code path fine but never appearing anywhere.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
# Indian registrars typically finalize and publish allotment in the evening
# of the allotment date, so that's when new IPOs are actually likely to
# show up — checking every 15 min then catches it close to immediately,
# without hammering the registrars' sites the rest of the day for no
# reason (allotment finalization isn't a fast-moving event outside that
# window).
EVENING_WINDOW_START_HOUR = 17
EVENING_CHECK_INTERVAL_SECONDS = 15 * 60
OFF_HOURS_CHECK_INTERVAL_SECONDS = 2 * 60 * 60

MARKET_HOURS_START_HOUR = 9
MARKET_HOURS_END_HOUR = 17
# Subscription/GMP numbers move continuously while bidding is open, so
# during market hours this refreshes every 5 min instead of the coarser
# 15 min used everywhere else -- off-hours stays at 2h since nothing is
# actually changing (no live bidding, no fresh GMP quotes) outside this
# window.
CATALOG_MARKET_HOURS_INTERVAL_SECONDS = 5 * 60
CATALOG_OFF_HOURS_INTERVAL_SECONDS = 2 * 60 * 60


def _next_refresh_delay_seconds() -> int:
    current_hour_ist = datetime.now(IST).hour
    if current_hour_ist >= EVENING_WINDOW_START_HOUR:
        return EVENING_CHECK_INTERVAL_SECONDS
    return OFF_HOURS_CHECK_INTERVAL_SECONDS


def _next_catalog_refresh_delay_seconds() -> int:
    current_hour_ist = datetime.now(IST).hour
    if MARKET_HOURS_START_HOUR <= current_hour_ist < MARKET_HOURS_END_HOUR:
        return CATALOG_MARKET_HOURS_INTERVAL_SECONDS
    return CATALOG_OFF_HOURS_INTERVAL_SECONDS


async def _periodic_refresh() -> None:
    while True:
        await asyncio.sleep(_next_refresh_delay_seconds())
        try:
            ok_count = await ipo_list_service.refresh()
            logger.info("IPO list refreshed (%d/3 registrars reachable)", ok_count)
        except Exception:
            logger.exception("IPO list refresh failed")


async def _periodic_catalog_refresh() -> None:
    while True:
        await asyncio.sleep(_next_catalog_refresh_delay_seconds())
        try:
            ok_count = await ipo_catalog_service.refresh()
            logger.info("IPO catalog refreshed (%d/2 sources reachable)", ok_count)
        except Exception:
            logger.exception("IPO catalog refresh failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await ipo_list_service.refresh()
    except Exception:
        logger.exception("Initial IPO list refresh failed")
    try:
        await ipo_catalog_service.refresh()
    except Exception:
        logger.exception("Initial IPO catalog refresh failed")
    refresh_task = asyncio.create_task(_periodic_refresh())
    catalog_refresh_task = asyncio.create_task(_periodic_catalog_refresh())
    yield
    refresh_task.cancel()
    catalog_refresh_task.cancel()
    await close_http_client()


app = FastAPI(title="IPO Allotment Checker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_ipos.router)
app.include_router(routes_allotment.router)
app.include_router(routes_push.router)
app.include_router(routes_device_pans.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
