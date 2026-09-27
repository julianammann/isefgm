"""Render the code-derived parts of the MS 4 documentation as Markdown.

Sources: the OpenAPI schema (endpoint summaries and descriptions), SQLAlchemy
metadata (table and column comments) and the Settings model (field descriptions).
Runs without a database. Usage: ``python -m giftmanager.export_docs [out_dir]``,
normally via ``mise run docs``. Conventions: docs/dokumentation.md.
"""

import sys
from pathlib import Path, PurePath
from typing import Any

from pydantic_core import PydanticUndefined
from sqlalchemy.dialects import postgresql

from giftmanager.core.config import Settings
from giftmanager.main import app
from giftmanager.models import Base

HEADER = "<!-- Generated from the code by `mise run docs`. Do not edit by hand. -->\n\n"


def _row(*cells: object) -> str:
    return "| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in cells) + " |\n"


def _table(*headers: str) -> str:
    return _row(*headers) + _row(*("---" for _ in headers))


def endpoints() -> str:
    """Render the interface chapter from the OpenAPI schema, grouped by tag."""
    schema: dict[str, Any] = app.openapi()
    intro = {t["name"]: t.get("description", "") for t in schema.get("tags", [])}
    rows: dict[str, list[str]] = {}
    for path, methods in sorted(schema["paths"].items()):
        for method, op in methods.items():
            tag = op.get("tags", ["(untagged)"])[0]
            codes = ", ".join(sorted(op.get("responses", {})))
            rows.setdefault(tag, []).append(
                _row(
                    f"`{method.upper()} {path}`",
                    f"`{op.get('operationId', '')}`",
                    op.get("summary", ""),
                    op.get("description", ""),
                    codes,
                )
            )
    out = HEADER + "# API\n\n"
    out += "Base URL `/api/v1`; errors are problem details (RFC 9457). "
    out += "Field descriptions and examples: `frontend/openapi.json` or `/docs`.\n\n"
    for tag, tag_rows in rows.items():
        out += f"## {tag}\n\n{intro.get(tag, '')}\n\n"
        out += _table("Endpoint", "operationId", "Purpose", "Behaviour", "Status") + "".join(
            tag_rows
        )
        out += "\n"
    return out


def tables() -> str:
    """Render the database chapter from table and column comments."""
    dialect = postgresql.dialect()
    out = HEADER + "# Database\n\n"
    out += "Tables and columns from `giftmanager.models`. Relationships and normalisation: "
    out += "`docs/datenmodell.md`. The comments are also stored in PostgreSQL (`\\d+ <table>`).\n\n"
    for table in Base.metadata.sorted_tables:
        out += f"## {table.name}\n\n{table.comment or ''}\n\n"
        out += _table("Column", "Type", "Nullable", "Description")
        for col in table.columns:
            flags: list[str] = []
            if col.primary_key:
                flags.append("PK")
            flags.extend(f"FK → {fk.column.table.name}.{fk.column.name}" for fk in col.foreign_keys)
            if col.unique:
                flags.append("unique")
            if col.index:
                flags.append("Index")
            desc = " ".join(filter(None, [col.comment, *(f"({f})" for f in flags)]))
            out += _row(
                f"`{col.name}`",
                col.type.compile(dialect=dialect),
                "yes" if col.nullable else "no",
                desc,
            )
        out += "\n"
    return out


def settings() -> str:
    """Render the configuration chapter from the `Settings` field descriptions."""
    out = HEADER + "# Configuration\n\n"
    out += "Environment variables, read from `.env` in the repo root (template `.env.example`) "
    out += "or from the process environment.\n\n"
    out += _table("Variable", "Default", "Meaning")
    for name, field in Settings.model_fields.items():
        value = field.default
        # Paths render with "/" on every OS, so the output does not depend on who ran it.
        if isinstance(value, PurePath):
            value = value.as_posix()
        default = "(required)" if value is PydanticUndefined else f"`{value}`"
        out += _row(f"`{name.upper()}`", default, field.description or "")
    return out


def main(out_dir: Path) -> None:
    """Write all generated documents into `out_dir`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, render in {
        "api.md": endpoints,
        "database.md": tables,
        "configuration.md": settings,
    }.items():
        # newline="\n": identical files on Windows, macOS and Linux.
        (out_dir / name).write_text(render().rstrip("\n") + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "../docs/generated"))
