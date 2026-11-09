"""Write expected outputs for the JavaScript parity test.

Covers every lexicon word, keyboard-substituted forms, and random texts with zero-width
characters and punctuation.

    python packages/sindhinorm/playground/make_parity_cases.py OUT.json
"""

from __future__ import annotations

import json
import random
import sys

import sindhinorm

norm = sindhinorm.default_normalizer()
words = list(norm.lexicon)
sub = str.maketrans({"ي": "ی", "ه": "ہ", "ڪ": "ک"})
rng = random.Random(7)
variants = []
for w in words:
    variants.append(w.translate(sub))
    variants.append(w.replace("ي", "ى").replace("ه", "ھ"))
    chars = list(w)
    for i, c in enumerate(chars):
        if c in sindhinorm.CLASSES and rng.random() < 0.5:
            chars[i] = rng.choice(sindhinorm.MEMBERS[sindhinorm.CLASSES[c]])
    variants.append("".join(chars))
all_words = sorted(set(words) | set(variants))
pieces = ["\u200c", "\u200d", " ", "، ", ". ", "\n", "ءَ", "123", "abc", "\u200c\u200c", "؟"]
texts = []
for _ in range(3000):
    parts = []
    for _ in range(rng.randint(1, 12)):
        parts.append(rng.choice(all_words))
        parts.append(rng.choice(pieces))
    texts.append("".join(parts))
cases = {
    "words": [[w, *norm.decide(w)] for w in all_words],
    "texts": [[t, norm.normalize(t), norm.explain(t)] for t in texts],
}
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(cases, f, ensure_ascii=False)
print(len(cases["words"]), "words,", len(texts), "texts")
