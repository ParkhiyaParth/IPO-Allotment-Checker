"""Scrapes Chittorgarh's GMP listing page.

The exact GMP report URL was not confirmed live at implementation time
(the site's main app is JS-rendered via Next.js/Turbopack, and the
obvious report-path guesses returned redirects/404 error shells rather
than a server-rendered table). GMP_URL below is a best-effort candidate;
if it stops matching, get_gmp_for_all() returns an empty list rather than
raising -- ipo_catalog_service.refresh() already treats "no GMP rows" as
"leave GMP as-is for this refresh cycle" (COALESCE-preserved), so a
mismatch here degrades to GMP showing "--" everywhere rather than
blocking calendar/subscription data. Revisit this URL and regex once
network access allows a real live capture.
"""

import re
from dataclasses import dataclass

from app.utils.http_client import get_http_client

GMP_URL = "https://www.chittorgarh.com/report/ipo-gmp-grey-market-premium/26/"

# Matches a table row containing a company name link and a GMP value cell.
_ROW_PATTERN = re.compile(
    r'<tr[^>]*>.*?<a[^>]*>([^<]+)</a>.*?class="[^"]*gmp[^"]*"[^>]*>\s*([\d.]+)\s*(?:\(([\d.]+)%\))?',
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class ChittorgarhGmpRow:
    company_name: str
    gmp_value: float | None = None
    gmp_percent: float | None = None


async def get_gmp_for_all() -> list[ChittorgarhGmpRow]:
    client = get_http_client()
    resp = await client.get(GMP_URL)
    resp.raise_for_status()
    html = resp.text

    rows = []
    for match in _ROW_PATTERN.finditer(html):
        company_name, gmp_value, gmp_percent = match.groups()
        rows.append(
            ChittorgarhGmpRow(
                company_name=company_name.strip(),
                gmp_value=float(gmp_value) if gmp_value else None,
                gmp_percent=float(gmp_percent) if gmp_percent else None,
            )
        )
    return rows
