from app.services import ipo_repository
from app.services.ipo_repository import CachedIpo


def test_get_all_returns_every_cached_ipo():
    records = [
        CachedIpo(
            id="linkintime-1",
            company_name="Alpha Ltd",
            registrar="linkintime",
            registrar_ipo_identifier="1",
            automation_supported=True,
            first_seen_at="2026-08-01T00:00:00+00:00",
        ),
        CachedIpo(
            id="bigshare-2",
            company_name="Beta Ltd",
            registrar="bigshare",
            registrar_ipo_identifier="2",
            automation_supported=True,
            first_seen_at="2026-08-02T00:00:00+00:00",
        ),
    ]
    ipo_repository.upsert_many(records)

    all_records = ipo_repository.get_all()

    assert {r.id for r in all_records} == {"linkintime-1", "bigshare-2"}
