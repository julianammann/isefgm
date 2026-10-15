"""Sphinx configuration for the backend code reference (Markdown pages for VitePress)."""

import builtins
import logging
from typing import Any

from sphinx.addnodes import pending_xref

project = "giftmanager"
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon"]

# Docstrings follow the Google style and use Markdown-like single backticks for code.
napoleon_google_docstring = True
napoleon_numpy_docstring = False
default_role = "code"

autodoc_typehints = "signature"
autodoc_member_order = "bysource"
autodoc_default_options = {"members": True}
# SQLAlchemy and Pydantic base classes bring docstrings that are not ours.
autodoc_inherit_docstrings = False

markdown_anchor_signatures = True
# Inherited SQLAlchemy docs reference labels that only exist in SQLAlchemy's own docs.
suppress_warnings = ["ref.ref"]


class _KeywordOnlyStarFilter(logging.Filter):
    """Drop the builder's warning about the `*` of keyword-only parameters.

    sphinx-markdown-builder cannot render that node and warns once per signature;
    build.py restores the `*` afterwards. Every other warning still shows.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Keep every record except the known keyword-only warning."""
        return "unknown node type: <abbreviation" not in record.getMessage()


def _exact_builtin_refs(app: Any, doctree: Any) -> None:
    """Resolve builtins in signatures by exact name only.

    Sphinx checks `hasattr(node, "refspecific")` instead of its value, so every
    signature type is looked up "fuzzy" by suffix: `type[T]` then matches the `type`
    fields of ValidationIssue and Problem. Builtins are never documented here, so
    dropping the flag leaves them unlinked; project types keep the fuzzy lookup.
    """
    for node in doctree.findall(pending_xref):
        if node.get("refdomain") == "py" and hasattr(builtins, node.get("reftarget", "")):
            node.attributes.pop("refspecific", None)


def setup(app: Any) -> None:
    """Install the filter on Sphinx's log handlers and the builtin-ref fix."""
    for handler in logging.getLogger("sphinx").handlers:
        handler.addFilter(_KeywordOnlyStarFilter())
    app.connect("doctree-read", _exact_builtin_refs)
