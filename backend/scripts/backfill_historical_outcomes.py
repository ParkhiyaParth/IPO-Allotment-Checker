"""One-off manual trigger for the historical-outcomes backfill, so the
dataset doesn't have to wait for the first daily refresh cycle after this
feature deploys. Safe to re-run anytime (upsert, not insert) -- run from
the backend/ directory: `python -m scripts.backfill_historical_outcomes`.
"""

import asyncio
import logging

from app.services import ipo_historical_backfill_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def main() -> None:
    count = await ipo_historical_backfill_service.backfill()
    print(f"Backfilled {count} historical IPO outcomes.")


if __name__ == "__main__":
    asyncio.run(main())
