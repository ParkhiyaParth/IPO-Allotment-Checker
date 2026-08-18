from app.services import gmp_history_repository


def test_append_and_get_recent_returns_newest_first():
    gmp_history_repository.append("catalog-acme", 10.0)
    gmp_history_repository.append("catalog-acme", 15.0)

    samples = gmp_history_repository.get_recent("catalog-acme")

    assert [s.gmp_percent for s in samples] == [15.0, 10.0]


def test_append_ignores_none_gmp():
    gmp_history_repository.append("catalog-acme", None)

    assert gmp_history_repository.get_recent("catalog-acme") == []


def test_append_prunes_beyond_max_samples():
    for value in range(15):
        gmp_history_repository.append("catalog-acme", float(value))

    samples = gmp_history_repository.get_recent("catalog-acme", limit=100)

    # Capped at 10 rows regardless of how many times append() is called --
    # bounded growth is the whole point on a 1GB RAM box.
    assert len(samples) == 10
    assert [s.gmp_percent for s in samples] == [14.0, 13.0, 12.0, 11.0, 10.0, 9.0, 8.0, 7.0, 6.0, 5.0]


def test_history_is_scoped_per_catalog_id():
    gmp_history_repository.append("catalog-acme", 10.0)
    gmp_history_repository.append("catalog-beta", 99.0)

    assert [s.gmp_percent for s in gmp_history_repository.get_recent("catalog-acme")] == [10.0]
    assert [s.gmp_percent for s in gmp_history_repository.get_recent("catalog-beta")] == [99.0]
