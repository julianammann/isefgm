"""Build the backend code reference as Markdown for the VitePress site.

Runs ``sphinx-apidoc`` and ``sphinx-build -b markdown`` on ``giftmanager`` and fixes
what the Markdown builder gets wrong. Usage: ``python docs/build.py <out_dir>``,
normally via ``mise run apidocs``.
"""

import re
import shutil
import sys
import tempfile
from pathlib import Path

from sphinx.cmd.build import build_main
from sphinx.ext.apidoc import main as apidoc_main

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent / "src" / "giftmanager"

INDEX = """# Backend

Code reference of the FastAPI backend (`giftmanager`), generated from docstrings and
type annotations. Layers: `api` (HTTP) → `services` (business rules) → `models`
(persistence); `schemas` define the HTTP contract, `core` holds infrastructure.
"""

# sphinx-markdown-builder drops the `*` that marks keyword-only parameters: it leaves
# ", ," in the middle of a signature and "(, " when every parameter is keyword-only
# (Pydantic models).
_KEYWORD_ONLY = re.compile(r"(?<=[(,]) ?, ")
# VitePress's search takes a section's ID from the first link in its heading. Sphinx
# puts cross-references into signature headings, so two sections can end up with the
# same ID and the build fails. Headings keep the type names, only without links.
_HEADING_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def _fix_page(text: str) -> str:
    lines = []
    for line in text.split("\n"):
        if line.startswith("#"):
            line = _HEADING_LINK.sub(r"\1", _KEYWORD_ONLY.sub(" *, ", line))
            line = line.replace("( *, ", "(*, ")
        lines.append(line)
    return "\n".join(lines)


def build(out_dir: Path) -> int:
    """Generate one Markdown page per module into `out_dir` and return Sphinx's exit code."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp)
        shutil.copy(HERE / "conf.py", src / "conf.py")
        # -e: one page per module, -M: module docs before submodules.
        apidoc_main(["-q", "-f", "-e", "-M", "-o", str(src), str(PACKAGE)])
        (src / "modules.rst").unlink()  # apidoc's own index; the site has its own
        (src / "index.rst").write_text(".. toctree::\n   :glob:\n\n   giftmanager*\n", "utf-8")
        shutil.rmtree(out_dir, ignore_errors=True)
        code = build_main(["-q", "-b", "markdown", str(src), str(out_dir)])

    shutil.rmtree(out_dir / ".doctrees", ignore_errors=True)
    for page in out_dir.glob("*.md"):
        text = page.read_text("utf-8")
        page.write_text(_fix_page(text), "utf-8", newline="\n")
    (out_dir / "index.md").write_text(INDEX, "utf-8", newline="\n")
    return code


if __name__ == "__main__":
    sys.exit(build(Path(sys.argv[1] if len(sys.argv) > 1 else "../docs/site/backend")))
