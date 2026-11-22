# Changelog

## 0.2.0 (unreleased)

* New default `mode="keyboard"`: only letters produced by Urdu, Persian or Arabic keyboards
  (ی ى ے ہ ك) are rewritten, only towards Sindhi letters, plus the guarded ک → ڪ. Words written
  entirely in Sindhi letters are left alone. On clean Sindhi news text (SiPOS) the share of
  changed tokens falls from 0.39% to 0.002%; restoration of keyboard-typed words rises from
  94.0% to 94.9%.
* `fold_heh=True` (CLI `--fold-heh`) merges the two heh shapes ه / ھ by frequency, as 0.1.0 did.
* `mode="frequency"` (CLI `--mode frequency`) reproduces the 0.1.0 rules exactly.
* Unknown words: keyboard letters get their usual Sindhi letter (ی ى ے → ي, ہ → ه, ك → ڪ).
* Browser playground: rule switch and heh option; JavaScript port matches Python in all modes.

## 0.1.0 (2026-11-10)

* First release: corpus-guided, native-validated normalizer with the bundled Sindhi Wikipedia
  word list, `normalize`, `explain`, and the `sindhinorm` command line.
