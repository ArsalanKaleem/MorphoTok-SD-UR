"""Build the single-file browser playground: template + sindhinorm.js + bundled lexicon.

    python packages/sindhinorm/playground/build_playground.py OUT.html

The JS port is checked against the Python package by ``parity_test.mjs``.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEXICON = HERE.parent / "src" / "sindhinorm" / "data" / "sd_lexicon.json.gz"
EXAMPLE = (
    "سنڌی ٻولی دنیا جی قدیم ٻولین مان ھڪ آهی. ہن ٻولیءَ ۾ ڪیترائی کتاب لکیا ویا آھن‌. "
    "شاھ عبداللطیف ڀٽائی جو رسالو مشھور آهي. اسان کی پنھنجی ٻوليءَ تي فخر آهي، ڪي شاعر به مشهور آهن."
)


def main() -> int:
    """Write the page."""
    page = (HERE / "template.html").read_text(encoding="utf-8")
    js = (HERE / "sindhinorm.js").read_text(encoding="utf-8")
    b64 = base64.b64encode(LEXICON.read_bytes()).decode("ascii")
    for key, value in (("/*__SINDHINORM_JS__*/", js), ("__LEXICON_B64__", b64),
                       ('"__EXAMPLE__"', json.dumps(EXAMPLE, ensure_ascii=False))):  # fmt: skip
        assert page.count(key) == 1, key
        page = page.replace(key, value)
    out = Path(sys.argv[1])
    out.write_text(page, encoding="utf-8")
    print(f"{out}: {out.stat().st_size / 1e3:.0f} kB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
