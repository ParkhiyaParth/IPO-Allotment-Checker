import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "ipo_cache.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ipo_cache (
    id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    registrar TEXT NOT NULL,
    registrar_ipo_identifier TEXT NOT NULL,
    automation_supported INTEGER NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    list_rank INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ipo_catalog (
    id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    nse_symbol TEXT,
    chittorgarh_slug TEXT,
    open_date TEXT,
    close_date TEXT,
    price_band_low REAL,
    price_band_high REAL,
    issue_price REAL,
    lot_size INTEGER,
    issue_size_cr REAL,
    gmp_value REAL,
    gmp_percent REAL,
    gmp_updated_at TEXT,
    sub_qib_offered INTEGER,
    sub_qib_applied INTEGER,
    sub_hni_offered INTEGER,
    sub_hni_applied INTEGER,
    sub_retail_offered INTEGER,
    sub_retail_applied INTEGER,
    sub_updated_at TEXT,
    boa_date TEXT,
    listing_date TEXT,
    listing_price REAL,
    current_price REAL,
    current_price_updated_at TEXT,
    linked_registrar_ipo_id TEXT,
    notified_apply_signal TEXT NOT NULL DEFAULT '',
    signal_accuracy_logged TEXT NOT NULL DEFAULT '',
    gmp_momentum_alerted_at TEXT NOT NULL DEFAULT '',
    auto_checked_boa TEXT NOT NULL DEFAULT '',
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS push_tokens (
    token TEXT PRIMARY KEY,
    registered_at TEXT NOT NULL,
    device_id TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS device_pans (
    id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    label TEXT NOT NULL,
    pan_encrypted TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_status TEXT,
    last_checked_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_device_pans_device_id ON device_pans(device_id);

CREATE TABLE IF NOT EXISTS signal_accuracy_log (
    catalog_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    signal_at_close TEXT NOT NULL,
    was_profitable INTEGER NOT NULL,
    logged_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gmp_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    catalog_id TEXT NOT NULL,
    gmp_percent REAL,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_gmp_history_catalog_id ON gmp_history(catalog_id, recorded_at);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    try:
        conn.execute("ALTER TABLE ipo_cache ADD COLUMN list_rank INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # column already exists (pre-existing cache file from before this migration)
    try:
        conn.execute("ALTER TABLE ipo_catalog ADD COLUMN boa_date TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists (pre-existing cache file from before this migration)
    try:
        conn.execute("ALTER TABLE ipo_catalog ADD COLUMN issue_price REAL")
    except sqlite3.OperationalError:
        pass  # column already exists (pre-existing cache file from before this migration)
    try:
        conn.execute("ALTER TABLE ipo_catalog ADD COLUMN notified_apply_signal TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists (pre-existing cache file from before this migration)
    try:
        conn.execute("ALTER TABLE ipo_catalog ADD COLUMN signal_accuracy_logged TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists (pre-existing cache file from before this migration)
    try:
        conn.execute("ALTER TABLE ipo_catalog ADD COLUMN gmp_momentum_alerted_at TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists (pre-existing cache file from before this migration)
    try:
        conn.execute("ALTER TABLE ipo_catalog ADD COLUMN auto_checked_boa TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists (pre-existing cache file from before this migration)
    try:
        conn.execute("ALTER TABLE push_tokens ADD COLUMN device_id TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists (pre-existing cache file from before this migration)
    return conn
