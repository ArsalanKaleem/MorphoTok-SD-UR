# sindhinorm

Spelling normalization for Sindhi text typed on mixed keyboards. No dependencies, Python ≥ 3.10.

Sindhi text often mixes look-alike Unicode letters from Urdu, Persian and Arabic keyboards:
Farsi yeh **ی** or alef maksura **ى** for Sindhi **ي**, Urdu heh-goal **ہ** or do-chashmi **ھ** for
**ه**, keheh **ک** or Arabic kaf **ك** for **ڪ**, plus stray zero-width characters. They look the
same but are different characters to software, so search, counting and NLP models treat one
word as several.

A fixed character map does not work for Sindhi, because **ک and ڪ are both real Sindhi
letters**: کي ("to") and ڪي ("some") are different words. sindhinorm decides **per word**,
using how often each spelling occurs in Sindhi Wikipedia, and never merges a pair that a
native Sindhi speaker judged to be different words.

```bash
pip install sindhinorm
```

Try it without installing: [sindhinorm Playground](https://arsalankaleem.github.io/MorphoTok-SD-UR/).

```python
from sindhinorm import normalize, explain

normalize("هي ڪتاب آهی")  # 'هي ڪتاب آهي'   (Farsi yeh fixed)
normalize("ڪي کي")  # 'ڪي کي'         (two different words: left alone)

explain("ھن آهی کري")
# [{'word': 'ھن',  'output': 'هن',  'rule': 'encoding-merge', 'count_in': 12528, 'count_out': 22047},
#  {'word': 'آهی', 'output': 'آهي', 'rule': 'encoding-merge', 'count_in': 0,     'count_out': 62425},
#  {'word': 'کري', 'output': 'کري', 'rule': 'native-keep',    'count_in': 14,    'count_out': 14}]
```

Command line:

```bash
sindhinorm < input.txt > output.txt
sindhinorm input.txt -o output.txt
sindhinorm explain "ھن آهی کري"
sindhinorm build-lexicon my_corpus.txt -o my_lexicon.json.gz   # your own word counts
sindhinorm -l my_lexicon.json.gz < input.txt > output.txt
```

## Rules

1. Unicode NFC. Zero-width non-joiners and joiners are removed unless a ZWNJ sits between
   two letters (native review found those mark compound and ال-name joins).
2. Candidate spellings: every combination of look-alike letters at the word's yeh
   {ي ی ى ے}, heh {ه ھ ہ} and kaf {ڪ ک ك} positions. The most frequent candidate wins if
   the rule allows the merge.
3. **Encoding-only** differences (ي/ی/ى, ه/ھ/ہ) are merged whenever the candidate is more
   frequent.
4. **Lexical** differences (any position involving ک, ڪ, ك or ے) are merged only if the
   rare form occurs ≤ 100 times **and** the candidate is ≥ 50× more frequent.
5. 24 pairs judged different or unsure by a native reviewer are never merged.
6. Words not in the lexicon only get the safest folds (ی ى → ي, ہ → ه).

`explain` reports which rule decided each word: `encoding-merge`, `lexical-merge`,
`native-keep`, `lexical-guard` (a more frequent variant exists but may be another word),
`already-canonical`, `no-variant-letters`, `unknown-fold` or `unknown-kept`.

## How well it works

Measured with the bundled lexicon (details and scripts:
[MorphoTok-SD-UR, docs/sdnorm.md](https://github.com/ArsalanKaleem/MorphoTok-SD-UR/blob/main/docs/sdnorm.md)):

| Test | Result |
|---|---|
| Text with ي replaced by ی (UD Sindhi test set, news) | **94.0%** of 4,511 altered words restored |
| Random-letter edits, same words (control) | 0.4% "restored": it does not undo arbitrary typos |
| Clean words changed | 1.35% |

**Limits.**
* Frequency cannot always tell a rare real word from a misspelling. The native keep-list
  covers the 24 reviewed cases. On the 150 reviewed pairs, the frequency rule alone merged
  with precision 0.87.
* The canonical spelling follows the Wikipedia majority, not a published standard. For
  example ھن → هن; some writers prefer ھ.
* One native reviewer. Sindhi only (no Urdu mode).

## Citing

Kaleem, A. (2026). *sindhinorm: a corpus-guided, native-validated spelling normalizer for Sindhi*
(Version 0.1.0) [Software]. Zenodo. https://doi.org/10.5281/zenodo.24093294

To cite whichever version is newest, use the all-versions DOI
[10.5281/zenodo.24093293](https://doi.org/10.5281/zenodo.24093293).

## Licences

* Code: MIT (`LICENSE`).
* Bundled word list: CC BY-SA 4.0 (`LICENSE-DATA`). It is derived from Sindhi Wikipedia
  (2023-11-01): 61,718 words seen at least twice, with counts.
