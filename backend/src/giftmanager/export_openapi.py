"""Print the OpenAPI schema as JSON to stdout; runs without a database.

Usage: ``python -m giftmanager.export_openapi > ../frontend/openapi.json``,
normally via ``mise run openapi``.
"""

import json
import sys

from giftmanager.main import app

if __name__ == "__main__":
    text = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    # Bytes, not text: a Windows console redirect would otherwise write CRLF.
    sys.stdout.buffer.write(text.encode())
