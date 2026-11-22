"""Build the single-file browser playground: template + sindhinorm.js + bundled lexicon.

    python packages/sindhinorm/playground/build_playground.py OUT.html
    python packages/sindhinorm/playground/build_playground.py site/index.html --standalone

``--standalone`` wraps the page in a full HTML document (doctype, viewport, ``lang``) for
static hosting such as GitHub Pages; without it the output is the fragment published as a
claude.ai artifact. The JS port is checked against the Python package by ``parity_test.mjs``.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEXICON = HERE.parent / "src" / "sindhinorm" / "data" / "sd_lexicon.json.gz"
EXAMPLE = (
    "سنڌی ٻولی دنیا جی قدیم ٻولین مان ہڪ آہی. ہن ٻولیءَ ۾ ڪیترائی کتاب لکیا ویا آہن‌. "
    "شاہ عبداللطیف ڀٽائی جو رسالو مشہور آہی. اسان کی پنہنجی ٻوليءَ تي فخر آهي، ڪي شاعر به مشهور آهن."
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
    if "--standalone" in sys.argv[2:]:
        head, sep, body = page.partition("</style>")
        assert sep, "template must contain one <style> block"
        head = head.replace('<meta charset="utf-8">\n', "", 1)
        page = (
            '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            '<meta name="description" content="Try sindhinorm, a spelling normalizer for Sindhi text '
            'typed on mixed keyboards, in your browser.">\n'
            + head
            + "body { margin: 0; }\n"
            + sep
            + "\n</head>\n<body>\n"
            + body.lstrip("\n")
            + "</body>\n</html>\n"
        )
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"{out}: {out.stat().st_size / 1e3:.0f} kB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
