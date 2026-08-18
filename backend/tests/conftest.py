import pytest

from app.db import database


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test_ipo_cache.sqlite3")


class FakeResponse:
    def __init__(self, json_data=None, text_data="", status_code=200):
        self._json_data = json_data
        self.text = text_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeAsyncClient:
    """Maps an exact URL to a canned FakeResponse. Tests key responses by
    the exact URL each client is expected to call; params are accepted but
    ignored for matching (clients under test use fixed base URLs)."""

    def __init__(self, responses: dict):
        self._responses = responses

    async def get(self, url, params=None, **kwargs):
        return self._responses[url]

    async def post(self, url, json=None, **kwargs):
        return self._responses[url]
