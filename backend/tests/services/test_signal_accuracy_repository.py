from app.services import signal_accuracy_repository
from app.services.signal_accuracy_repository import SignalAccuracyEntry


def _entry(**overrides) -> SignalAccuracyEntry:
    defaults = dict(
        catalog_id="catalog-acme",
        company_name="Acme Ltd",
        signal_at_close="strong_apply",
        was_profitable=True,
        logged_at="2026-08-18T00:00:00Z",
    )
    defaults.update(overrides)
    return SignalAccuracyEntry(**defaults)


def test_get_stats_empty_when_nothing_logged():
    stats = signal_accuracy_repository.get_stats()

    assert stats == {"total": 0, "correct": 0, "hit_rate": None, "by_signal": {}}


def test_strong_apply_correct_when_profitable():
    signal_accuracy_repository.insert(_entry(signal_at_close="strong_apply", was_profitable=True))

    stats = signal_accuracy_repository.get_stats()

    assert stats["total"] == 1
    assert stats["correct"] == 1
    assert stats["hit_rate"] == 1.0
    assert stats["by_signal"]["strong_apply"] == {"total": 1, "correct": 1, "hit_rate": 1.0}


def test_skip_correct_when_not_profitable():
    # "skip" is a "won't profit" call, so it's correct when the IPO did
    # NOT turn a profit -- the opposite polarity from strong_apply/consider.
    signal_accuracy_repository.insert(
        _entry(catalog_id="catalog-beta", signal_at_close="skip", was_profitable=False)
    )

    stats = signal_accuracy_repository.get_stats()

    assert stats["correct"] == 1
    assert stats["by_signal"]["skip"]["correct"] == 1


def test_skip_incorrect_when_actually_profitable():
    signal_accuracy_repository.insert(
        _entry(catalog_id="catalog-beta", signal_at_close="skip", was_profitable=True)
    )

    stats = signal_accuracy_repository.get_stats()

    assert stats["correct"] == 0
    assert stats["by_signal"]["skip"]["correct"] == 0


def test_insert_does_not_double_log_same_catalog_id():
    signal_accuracy_repository.insert(_entry(was_profitable=True))
    signal_accuracy_repository.insert(_entry(was_profitable=False))  # same catalog_id, ignored

    stats = signal_accuracy_repository.get_stats()

    assert stats["total"] == 1
    assert stats["correct"] == 1  # the first (profitable) insert wins, second is a no-op
