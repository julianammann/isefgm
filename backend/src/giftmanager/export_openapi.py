"""Print the OpenAPI schema as JSON to stdout; runs without a database.

Usage: ``python -m giftmanager.export_openapi > ../frontend/openapi.json``,
normally via ``mise run openapi``.
"""

import json
import os
import sys

# main reads settings at import, which require DATABASE_URL; the export never connects.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://unused@localhost/unused")

from giftmanager.main import app

if __name__ == "__main__":
    text = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    # Bytes, not text: a Windows console redirect would otherwise write CRLF.
    sys.stdout.buffer.write(text.encode())
