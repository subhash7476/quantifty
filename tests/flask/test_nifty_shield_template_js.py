"""The NiftyShield dashboard's inline JS must parse.

2026-09-08: an apostrophe inside a single-quoted string ("today's") ended the
string early and made the whole <script> block a syntax error. Every paint
function died, so the operator's window showed "Waiting for the window" with
every cell "--" while a live session was running and healthy. Nothing else in
the suite reads this file: the blueprint tests exercise JSON endpoints, and a
broken template still returns HTTP 200.

Node is the only JS parser on hand; skip where it is absent rather than fail,
since this guards a template, not the platform.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

TEMPLATE = (Path(__file__).resolve().parents[2]
            / "flask_app" / "templates" / "nifty_shield" / "index.html")


def _inline_js() -> str:
    html = TEMPLATE.read_text(encoding="utf-8")
    blocks = re.findall(r"<script>(.*?)</script>", html, re.S)
    assert blocks, "no inline <script> block found in the dashboard template"
    return "\n".join(blocks)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_dashboard_inline_js_parses(tmp_path):
    js = tmp_path / "dashboard.js"
    js.write_text(_inline_js(), encoding="utf-8")
    result = subprocess.run(["node", "--check", str(js)],
                            capture_output=True, text=True)
    assert result.returncode == 0, (
        f"dashboard inline JS is not parseable:\n{result.stderr}")
