"""Geschenke-Manager backend (FastAPI, SQLAlchemy 2.0 async, Alembic).

The ASGI app is `giftmanager.main.app`. Requests flow `api` (HTTP) -> `services`
(business rules) -> `models` (persistence); `schemas` define the HTTP contract and
`core` holds cross-cutting infrastructure.
"""

from importlib.metadata import version

__version__ = version("giftmanager")
