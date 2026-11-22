# sindhinorm

Spelling normalization for Sindhi text typed on mixed keyboards. No dependencies, Python ≥ 3.10.

Sindhi text often mixes look-alike Unicode letters from Urdu, Persian and Arabic keyboards:
Farsi yeh **ی** or alef maksura **ى** for Sindhi **ي**, Urdu heh-goal **ہ** or do-chashmi **ھ** for
**ه**, keheh **ک** or Arabic kaf **ك** for **ڪ**, plus stray zero-width characters. They look the
same but are different characters to software, so search, counting and NLP models treat one
word as several.

A fixed character map does not work for Sindhi, because **ک and ڪ are both real Sindhi
letters**: کي ("to") and ڪي ("some") are different words. sindhinorm decides **per word**: it
replaces only the letters a non-Sindhi keyboard produces, uses how often each spelling occurs in
Sindhi Wikipedia to choose between Sindhi letters, and never merges a pair that a native Sindhi
speaker judged to be different words. Text already written in Sindhi letters is left alone.

```bash
pip install sindhinorm
```

Try it without installing: [sindhinorm Playground](https://arsalankaleem.me/MorphoTok-SD-UR/).

```python
from sindhinorm import Normalizer, default_normalizer, explain, normalize

normalize("هي ڪتاب آهی")  # 'هي ڪتاب آهي' (Farsi yeh fixed)
normalize("ڪي کي")  # 'ڪي کي' (two different words: left alone)

explain("ہن آهی کري کتاب")
# [{'word': 'ہن',   'output': 'هن',   'rule': 'encoding-merge', 'count_in': 0,  'count_out': 22047},
#  {'word': 'آهی',  'output': 'آهي',  'rule': 'encoding-merge', 'count_in': 0,  'count_out': 62425},
#  {'word': 'کري',  'output': 'کري',  'rule': 'native-keep',    'count_in': 14, 'count_out': 14},
#  {'word': 'کتاب', 'output': 'ڪتاب', 'rule': 'lexical-merge',  'count_in': 16, 'count_out': 6786}]

lexicon = default_normalizer().lexicon
Normalizer(lexicon, fold_heh=True)  # also merge the two heh shapes (ھن -> هن) by frequency
Normalizer(lexicon, mode="frequency")  # the 0.1.0 rules, for reproducing earlier results
```

Command line:

```bash
sindhinorm < input.txt > output.txt
sindhinorm input.txt -o output.txt
sindhinorm explain "ہن آهی کري"
sindhinorm --fold-heh < input.txt > output.txt
sindhinorm --mode frequency < input.txt > output.txt     # 0.1.0 rules
sindhinorm build-lexicon my_corpus.txt -o my_lexicon.json.gz   # your own word counts
sindhinorm -l my_lexicon.json.gz < input.txt > output.txt
```

## Rules (keyboard mode, the default since 0.2.0)

1. Unicode NFC. Zero-width non-joiners and joiners are removed unless a ZWNJ sits between
   two letters (native review found those mark compound and ال-name joins).
2. Only letters that Urdu, Persian or Arabic keyboards produce instead of Sindhi ones are
   rewritten: ی ى ے → ي, ہ → ه or ھ, ك → ڪ or ک. These letters are never written into a word.
3. Where there is a choice of Sindhi letter, the spelling more frequent in Sindhi Wikipedia wins.
4. An Urdu keyboard has no ڪ, so ک is often typed for it. ک → ڪ is allowed only if the typed
   form occurs ≤ 100 times **and** the other form is ≥ 50× more frequent.
5. A word written entirely in Sindhi letters is otherwise left as it is. Both heh shapes
   (ه, ھ) are used in Sindhi; `fold_heh=True` merges them by frequency.
6. 24 pairs judged different or unsure by a native reviewer are never merged.
7. Words not in the word list get the usual Sindhi letter for each keyboard letter
   (ی ى ے → ي, ہ → ه, ك → ڪ).

`mode="frequency"` restores the 0.1.0 rules: the most frequent look-alike spelling wins, in
either direction. `explain` reports which rule decided each word: `encoding-merge`,
`lexical-merge`, `native-keep`, `lexical-guard` (a more frequent variant exists but may be another
word), `already-canonical`, `no-variant-letters`, `unknown-fold` or `unknown-kept`.

## How well it works

Measured with the bundled word list (details and scripts:
[MorphoTok-SD-UR, docs/sdnorm.md](https://github.com/ArsalanKaleem/MorphoTok-SD-UR/blob/main/docs/sdnorm.md)):

| Test | 0.2.0 (default) | 0.1.0 rules |
|---|---|---|
| UD Sindhi test, every ي typed as ی: altered words restored | **94.9%** | 94.0% |
| Same words, one random letter changed (control): "restored" | 0.3% | 0.4% |
| Clean UD Sindhi words changed | **0.03%** | 1.35% |
| Clean Sindhi news (SiPOS, 293,683 tokens) changed | **0.002%** | 0.39% |

**Does it help NLP models?** In a preregistered test, a part-of-speech tagger trained on Sindhi
news (SiPOS) scored 0.982 on clean text but only 0.494 on the same text typed on an Urdu keyboard.
Normalizing with 0.2.0 brought it back to **0.924** (+0.43), with no measurable change on clean
text (−0.002, interval includes 0). Details: [docs/findings_norm_pos.md](https://github.com/ArsalanKaleem/MorphoTok-SD-UR/blob/main/docs/findings_norm_pos.md).

The 0.1.0 rules followed Wikipedia's majority spelling even into non-Sindhi letters, for example
عبدالقدير → عبدالقدیر, or between real words, لڪيل → لکيل. Version 0.2.0 makes neither change.

**Limits.**
* Frequency cannot always tell a rare real word from a typing slip when ک and ڪ both give real
  words. The native keep-list covers the 24 reviewed cases.
* One native reviewer. Sindhi only (no Urdu mode).

## Citing

Kaleem, A. (2026). *sindhinorm: a corpus-guided, native-validated spelling normalizer for Sindhi*
(Version 0.2.0) [Software]. Zenodo. https://doi.org/10.5281/zenodo.24448229

To cite whichever version is newest, use the all-versions DOI
[10.5281/zenodo.24093293](https://doi.org/10.5281/zenodo.24093293).

## Licences

* Code: MIT (`LICENSE`).
* Bundled word list: CC BY-SA 4.0 (`LICENSE-DATA`). It is derived from Sindhi Wikipedia
  (2023-11-01): 61,718 words seen at least twice, with counts.
