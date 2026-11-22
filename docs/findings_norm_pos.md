# Spelling normalization and POS tagging (H9; PREREG.md §12)

Preregistered in Amendment 8 (tag `prereg-v9`) before any tagger was trained; moved to a Kaggle
T4 GPU by Amendment 9 (`prereg-v10`) after a CPU attempt that finished no run. Results:
[`results/norm_pos/report_sipos.md`](../results/norm_pos/report_sipos.md) (primary) and
[`results/norm_pos/report_ud_sd.md`](../results/norm_pos/report_ud_sd.md) (replication).

**Question.** Sindhi is often typed on Urdu keyboards, which have no ڪ key and put ی and ہ where
Sindhi uses ي and ه. Does `sindhinorm` give a part-of-speech tagger back the accuracy that such
text costs it, without harming text that was typed correctly?

**Set-up.** SiPOS (Ali, Xu and Kumar, 2021; Sindhi news; 236,866 training and 28,592 test
tokens), and UD Sindhi-Isra as a replication. The test text is scored three ways: clean;
retyped as an Urdu keyboard would (ي → ی, ه → ہ, ڪ → ک in every token that has them: 61% of
SiPOS test tokens, 56% of UD); and a control in which the same tokens get one random letter
changed. BiLSTM taggers with whole-word (`word`) or character (`char`) input are trained with
no normalizer, with the 0.1.0 rules or with the 0.2.0 keyboard mode, 3 seeds each (36 runs).
The same normalizer is applied to training and test text.

## Primary result (SiPOS, word tagger): it helps, and it does no harm

| Test text | No normalizer | 0.1.0 rules | **0.2.0 keyboard** | 0.2.0 − none (95% CI) | Preregistered verdict |
|---|---|---|---|---|---|
| Urdu-keyboard typed | 0.494 | 0.925 | **0.924** | **+0.430** [+0.382, +0.478] | **helps** (H9a: ≥ +0.05, CI > 0) |
| Clean | 0.982 | 0.981 | 0.981 | −0.002 [−0.013, +0.010] | **no harm** (H9b) |
| Random-letter control | 0.501 | 0.481 | 0.500 | −0.000 [−0.112, +0.112] | (not expected to help) |

Keyboard typing halves the word tagger's accuracy, because 61% of the tokens become words it has
never seen. With the normalizer it recovers **88%** of what it lost. On the altered tokens alone,
accuracy rises from 0.188 to 0.886; the normalizer restored 88.3% of them to the exact clean
spelling, and the tagger gets most of those right. It does not undo random typos, as intended.

## Secondary results

* **Character tagger (SiPOS).** Character input alone does not protect against this kind of
  typing: accuracy falls from 0.978 to 0.631, because the substitutions hit the most frequent
  function words (جي, کي, ته …) as well. The normalizer adds **+0.299** [+0.162, +0.437]
  (recovery 87%) and changes clean accuracy by −0.001 [−0.007, +0.004].
* **UD Sindhi replication.** Word tagger +0.260 [+0.224, +0.297] on keyboard-typed text
  (recovery 91%), clean +0.004 [−0.009, +0.016]. Character tagger +0.172 [−0.023, +0.367]; the
  interval includes 0 because the unnormalized baseline varied between seeds (keyboard-typed
  accuracy 0.80, 0.68 and 0.66), while all three normalized runs reached 0.88 to 0.89. Its clean
  accuracy rose by +0.004 [+0.001, +0.007].
* **0.2.0 vs 0.1.0.** No detectable difference in tagging accuracy in any cell (all intervals
  include 0). The 0.1.0 rules change 0.39% of clean SiPOS tokens, too few to move a tagger's
  accuracy measurably. The case for 0.2.0 rests on not rewriting correct text (0.002% of SiPOS
  tokens changed, and no non-Sindhi letters written), not on tagging accuracy.

## What this means

For a tagger trained on correctly typed Sindhi, text typed on an Urdu keyboard is a severe
problem (accuracy 0.98 → 0.49), and `sindhinorm` removes most of it at no measurable cost on
correct text. The remaining gap (0.924 against 0.981) comes from the 12% of altered tokens the
normalizer does not restore (2,053 of 17,543 in SiPOS test):

| Why a keyboard-typed token was not restored | Share | Most frequent |
|---|---|---|
| blocked by the native keep-list | 59% | تہ for ته (712), کی for کي (503) |
| ک not changed back to ڪ (guard, unknown word or keep-list) | 36% | کو for ڪو (68), کئی for ڪئي (53), کا for ڪا (38) |
| a different heh shape chosen for ہ | 5% | شہر → شھر for شهر (29) |

Most of the gap is two very frequent words. The native reviewer judged تہ/ته and کی/کي to be
different words in isolation, and they are Urdu words, so the keep-list never merges them. In
keyboard-typed Sindhi they are almost always typing slips. Deciding these pairs from the
surrounding words, instead of always keeping them, is the clearest next improvement.

## Caveats

* The keyboard model is synthetic: it applies all three substitutions to every affected token,
  covers only look-alike letters, and leaves other Sindhi-only letters (ٻ, ڄ, ڏ …) untouched.
  Real mixed-keyboard text is messier and may be less consistent.
* One domain (news), one tagger architecture, three seeds. The UD test set was used before in
  the exploratory POS study.
* The SiPOS observations motivated the 0.2.0 design (PREREG §12, "known before freezing"); the
  tagging results themselves were not seen before the freeze.

## Provenance

Kaggle T4, 36 runs (18 per dataset, device `cuda`). The downloaded working copy of the code
(`19_norm_pos.py`, `morphtok.models.tagger`, `sindhinorm` including its word list) is identical to
the repository at `prereg-v10` after normalizing line endings. Downloaded `results (1).zip`
sha256 `418fec70…16190a`; `runs_sipos.jsonl` `52dcc72d…0b0e29`, `runs_ud_sd.jsonl`
`2920eb8e…179f02`, `per_token_sipos.jsonl` `eabad75f…c7abde`, `per_token_ud_sd.jsonl`
`beb85f3e…8490da`.
