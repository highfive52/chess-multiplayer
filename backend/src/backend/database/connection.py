import os
from typing import Optional

DATABASE_URL_ENV = "DATABASE_URL"


def get_database_url() -> Optional[str]:
    return os.environ.get(DATABASE_URL_ENV)


def connect():
    """Return a psycopg Connection configured from `DATABASE_URL`.

    This module intentionally keeps the surface minimal so the project can
    choose sync or async DB approaches later.
    """
    database_url = get_database_url()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    try:
        import psycopg
    except Exception as e:
        raise RuntimeError("psycopg is required to connect to the database") from e

    # Allow SQLAlchemy-style scheme override such as:
    #   postgresql+psycopg://user:pass@host/db
    # psycopg.connect expects a libpq-style URL (e.g. postgresql://...).
    # Normalize by removing any +driver suffix on the scheme.
    def _normalize_url(url: str) -> str:
        if "://" not in url:
            return url
        scheme, rest = url.split("://", 1)
        if "+" in scheme:
            scheme = scheme.split("+", 1)[0]
            return f"{scheme}://{rest}"
        return url

    normalized = _normalize_url(database_url)
    conn = psycopg.connect(normalized)
    return conn
