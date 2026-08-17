import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_allotment, routes_ipos, routes_push
from app.config import settings
from app.services import ipo_list_service
from app.utils.http_client import close_http_client

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


def _next_refresh_delay_seconds() -> int:
    current_hour_ist = datetime.now(IST).hour
    if current_hour_ist >= EVENING_WINDOW_START_HOUR:
        return EVENING_CHECK_INTERVAL_SECONDS
    return OFF_HOURS_CHECK_INTERVAL_SECONDS


async def _periodic_refresh() -> None:
    while True:
        await asyncio.sleep(_next_refresh_delay_seconds())
        try:
            ok_count = await ipo_list_service.refresh()
            logger.info("IPO list refreshed (%d/3 registrars reachable)", ok_count)
        except Exception:
            logger.exception("IPO list refresh failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await ipo_list_service.refresh()
    except Exception:
        logger.exception("Initial IPO list refresh failed")
    refresh_task = asyncio.create_task(_periodic_refresh())
    yield
    refresh_task.cancel()
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
