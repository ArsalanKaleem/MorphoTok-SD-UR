# Pilot findings (2026-10-29), exploratory

**Status.** Everything here is *pilot* evidence: the preregistration is not frozen,
evaluation sets are dev splits, and the morphological "gold" for Gates 2–3 is **silver**
(derived from manually annotated lemmas), except the Zia ZWNJ set, which is human
annotation. Vocabulary sizes are matched within each comparison. "Over seeds" means 3
seeds that vary a 90% training subsample. Numbers come from the run records in `runs/`
(IDs below).

## 1. ZWNJ is a normative-orthography device that real text almost never uses

| Corpus | Words | ZWNJ per 100k words | Source runs |
|---|---|---|---|
| Sindhi Wikipedia (2023-11-01, all eligible lines) | 3.83M | 2.9 | `SD-sindhi_audit-G1-*` / `SD-G1-zwnj-audit` |
| Sindhi FineWeb-2 (web, test split) | 1.56M | **0** (see caveat) | `SD-sindhi_web_audit-G1-*` |
| Sindhi UD-Isra (news, folk stories) | 90k | 1.1 (1 token) | `scripts/build_silver.py` log |
| Urdu Wikipedia | 35.6M | 10.1 | `UR-urdu_audit-G1-*` / `UR-G1-zwnj-audit` |
| Urdu FineWeb-2 (web) | 25.2M | **0** (see caveat) | `UR-urdu_web_audit-G1-*` |
| Urdu UD-UDTB (news) | 138k | 0.7 (1 token) | build log |
| **Urdu, Zia et al. 2018 (human-annotated to normative rules)** | 111k | **5,779** | `data/gold/ur_zia_zwnj.stats.json` |

The words that Zia et al.'s annotators wrote with ZWNJ (1,811 types) occur **joined,
without ZWNJ, 119,813 times** in Urdu Wikipedia and **with ZWNJ 46 times**. In FineWeb-2
they occur 126,677 times joined and never with ZWNJ, but see the caveat below. The sub-word boundaries that
ZWNJ is meant to mark exist in the language's normative orthography but are invisible in
real digital text.

**Caveat (web domain):** FineWeb-2 contains *no* ZWNJ at all in either language (it does
contain other characters such as ZWSP). Its processing pipeline probably strips or
normalizes format characters, which has not been verified. The web rows therefore say
nothing about writers' behaviour. The Wikipedia and UD evidence (where ZWNJ does
occur, rarely) is the trustworthy part of the comparison. Corollary: tokenizers trained
on FineWeb-2-style data never see ZWNJ, whatever the policy.

Consequence for H1 (Gate 0): at matched V ∈ {2000, 4000} and 3 seeds, every ZWNJ policy
(preserve / remove / boundary marker) changes tokens per word by ≤ 0.001 in both
languages (`SD-G0-*`, `UR-G0-*`). **The ZWNJ-specific part of the original proposal has
no measurable leverage on real text.** The gap between normative and real usage, and its
tokenization consequences, is the reportable finding.

## 2. Other orthographic variation is larger than ZWNJ (descriptive only)

Off-standard Arabic code points in **Urdu** text, words per 1,000
(`scripts/codepoint_variants.py`; `*.variants.json` next to the corpora):

| | Arabic yeh U+064A | Arabic kaf U+0643 | Arabic heh U+0647 | ZWNJ |
|---|---|---|---|---|
| Urdu Wikipedia | 1.38 | 0.42 | 0.71 | ≈0.10 |
| Urdu web | 1.46 | 0.71 | 1.09 | 0 (stripped?) |

17,159 (Wikipedia) and 15,163 (web) Urdu word groups are spelled with more than one yeh
variant. For **Sindhi** the same code points are *distinct letters* (ک/ڪ, ه/ھ), so no
folding is implied. Urdu-style letters (Farsi yeh 1.3/1k, heh goal 5.2/1k in Sindhi
Wikipedia) may indicate Urdu-influenced spelling. **Nothing was folded.** Deciding
equivalences needs native-speaker approval (the `selective` policy).

## 3. Silver supervision during training only improves segmentation of unseen lemmas

Set-up: supervision = boundaries derived from manually annotated (form, lemma) pairs
(UD Sindhi-Isra; UD Urdu-UDTB + UniMorph) for **train-split lemmas only**. Evaluation on
**dev-split lemmas the supervision never covered** (Sindhi 961 types, Urdu 1,618).
Corpus: 5,000-line Wikipedia pilots.

Held-out-lemma results, mean over 3 seeds (`SD-EVAL-*`, `UR-EVAL-*`):

| | V | Unigram F1 / R / coherence | + train-only hard supervision | ΔF1 [t-CI over seeds] | Δ tokens/word |
|---|---|---|---|---|---|
| Sindhi | 2000 | 0.179 / 0.468 / 0.427 | 0.198 / 0.518 / 0.457 | +0.019 [+0.010, +0.027] | +0.031 |
| Sindhi | 4000 | 0.189 / 0.392 / 0.411 | 0.229 / 0.479 / 0.462 | +0.039 [+0.029, +0.050] | +0.044 |
| Urdu | 2000 | 0.147 / 0.665 / 0.560 | 0.158 / 0.719 / 0.605 | +0.011 [+0.010, +0.012] | +0.017 |
| Urdu | 4000 | 0.160 / 0.575 / 0.509 | 0.173 / 0.622 / 0.532 | +0.014 [+0.011, +0.016] | +0.021 |

* **Negative control** (`*-randctrl-*`): random boundaries with the same coverage and
  per-word count give the same tokens per word (Sindhi V=4000: 1.530 vs 1.531) but
  F1/R/coherence of 0.197/0.406/0.422 (Sindhi) and 0.145/0.522/0.476 (Urdu, *below*
  plain Unigram). The gain is therefore **not** a token-length or boundary-density effect.
* **Hard ≥ soft.** Soft λ=2 gives at most +0.009 (Sindhi) and +0.006 (Urdu). By the
  Gate 3 rule, the soft prior is unnecessary complexity at this λ (λ sweep: §5).
* **Decode-time constraints add nothing on held-out words**, by construction. The
  train-only variant needs **no analyzer at inference** and matches `unigram_hard`.
* **Unigram > BPE** on held-out lemmas (−0.04 to −0.05 F1 Sindhi, −0.007 to −0.014
  Urdu), consistent with prior work (bostrom2020, vemula2025).
* Absolute F1 is low because silver marks one inflectional boundary per word, and any
  other predicted boundary counts as a false positive. Recall and paradigm coherence are
  the more informative columns.

**Novelty status.** The training procedure is posterior regularization with a fixed
dual (ganchev2010), and its hard form is morphological pre-segmentation
(brahma2025, vemula2025). Neither is new. vemula2025 report that pre-segmentation does
not help Unigram *downstream* in Telugu. The pilot instead measures *intrinsic
generalization to unseen lemmas* in Sindhi and Urdu, with a fertility-matched negative
control. Whether that is new still needs a targeted literature check before any claim.

## 4. Transferring normative ZWNJ annotations to ZWNJ-free text: little gain

Supervision from 1,247 Zia training compound types, evaluated on 291 held-out
compound types (recall is the meaningful metric; `UR-urdu_zia-EVAL-*`):

| V | BPE R | Unigram R | + train-only hard (Zia) | ΔF1 over seeds |
|---|---|---|---|---|
| 2000 | 0.836 | 0.927 | 0.928 | +0.001 [−0.003, +0.004] |
| 4000 | 0.816 | 0.911 | 0.914 | +0.006 [+0.001, +0.011] |

**Plain Unigram already recovers about 91–93% of the invisible compound boundaries**,
because compound members are frequent words, so the supervision has little to add.
Combining Zia with lemma silver did not help either (`UR-urdu_zia_combined-*`; CIs
include 0).

## 5. Ablations (Sindhi V=4000, base = soft train-only; `SD-ABL-*`)

| Condition | Dev F1 (mean±sd, 3 seeds) |
|---|---|
| λ = 0 (plain) / 0.5 / 2 / 8 / 64 | 0.189 / 0.192 / 0.199 / 0.227 / **0.229** |
| hard (train-only) | **0.229** |
| penalty linear / uniform (λ = 2) | 0.199 / 0.201 |
| coverage 1.0 / 0.5 / 0.25 (λ = 2) | 0.199 / 0.194 / 0.192 |
| random boundaries (λ = 2) | 0.193 |

* **F1 rises monotonically with λ and reaches the hard value**, which also checks the
  soft → hard limit (`docs/lattice.md`) on real data. There is no interior optimum, so by
  the B2 rule the soft prior is unnecessary and hard train-only supervision is the
  simplest variant that works.
* Confidence weighting cannot be tested with silver data: the confidences are almost
  constant (0.8 × agreement ≈ 0.8), so linear ≈ uniform by construction.
* **Urdu** (`UR-ABL-*`) replicates it: λ = 0 / 0.5 / 2 / 8 / 64 gives 0.160 / 0.161 / 0.165 /
  0.171 / 0.173, and hard = 0.173. Coverage 0.5 / 0.25 gives 0.163 / 0.163; random
  boundaries give 0.161.

### 5c. Gate 5 proxy: token-bigram bits per character (`*-LMPROXY-*`; NOT a neural LM)

| | V | BPE | Unigram | + train-only hard |
|---|---|---|---|---|
| Sindhi | 2000 | 3.582 | **3.562** | 3.575 |
| Sindhi | 4000 | 3.605 | **3.588** | 3.610 |
| Urdu | 2000 | 3.311 | **3.288** | 3.295 |
| Urdu | 4000 | 3.356 | **3.325** | 3.337 |

On this crude proxy the alignment gain does **not** transfer. The supervised tokenizer
costs about 0.2–0.6% bits per character, consistent with H7 and with vemula2025.
Settling it needs a neural LM under the controls in `configs/eval/downstream.yaml`.

## 6. Web domain (FineWeb-2) and Gate 2 coverage

* **Gate 0, web** (`SD-sindhi_web-G0-*`, `UR-urdu_web-G0-*`; V ∈ {2000, 4000}, 3 seeds): all
  ZWNJ policies are identical because there is no ZWNJ. Tokens per word: Sindhi BPE
  1.575/1.384 vs Unigram 1.600/1.402; Urdu BPE 1.541/1.343 vs Unigram 1.529/1.340.
* **Gate 2** (silver analyzer, train lemmas only): type/token coverage of the pilot
  training corpus is 8.6% / 27.4% (Sindhi) and 15.1% / 42.1% (Urdu). It covers 0 held-out
  dev types by construction, so its precision cannot be measured without independent
  gold. **H3 remains untested** for any real analyzer.

## 7. Scale check: 20k-line Sindhi corpus (`SD-sindhi_20k-*`)

| V | Unigram F1 / R / coherence | + train-only hard | ΔF1 [t-CI over seeds] | Δ tokens/word |
|---|---|---|---|---|
| 4000 | 0.189 / 0.395 / 0.382 | 0.222 / 0.469 / 0.457 | +0.033 [+0.026, +0.040] | +0.044 |
| 8000 | 0.189 / 0.303 / 0.306 | 0.228 / 0.371 / 0.366 | +0.039 [+0.035, +0.043] | +0.052 |

The gain holds with 4× more text and twice the vocabulary. Plain Unigram's paradigm
coherence *falls* as V grows (0.41 → 0.38 → 0.31 across the 5k/V4000, 20k/V4000 and
20k/V8000 settings), consistent with memorising whole inflected forms. Supervision
slows that erosion.

## 8. What would change these conclusions

* A **human** boundary gold set for Sindhi/Urdu inflection: silver derivation assumes
  stem = LCP(form, lemma) and misses prefixes and stacked suffixes.
* Test-split evaluation after a preregistration freeze. Everything above is dev.
* Larger corpora and vocabularies (§7), and downstream checks (Gate 5): vemula2025 found
  alignment gains need not transfer, and the bigram proxy (§5c) points the same way.
* Whether FineWeb-2 strips format characters (§1 caveat).

## 9. Recommended next steps (smallest informative experiments first)

1. **Human gold, ~300 Sindhi + ~300 Urdu held-out word types** (inflection boundaries),
   using `audit/annotation_guidelines.md`. This turns §3 from silver to gold evidence, and
   is the single most valuable addition.
2. **Label the two ZWNJ annotation sheets** (Sindhi: all 109 Wikipedia occurrences; Urdu:
   236 sampled) to close H2 for *actual* usage.
3. **Small neural LM (Gate 5)** on one T4: `unigram` vs `unigram_hard_trainonly`, same
   character budget, 3 seeds, to test whether the intrinsic gain matters downstream.
4. **Native-speaker review of the Urdu yeh/kaf/heh variant groups** (§2). If approved, a
   `selective` folding rule has measurable reach (≈ 0.3% of words, about 30× ZWNJ in
   Wikipedia).
5. **Freeze the preregistration** with thresholds set from these pilot variances, then
   evaluate once on test.

## 10. Final audit of this pilot

* Lint: `ruff check` and `ruff format --check` clean. Tests: see the session summary
  (re-run after the last code change).
* All runs, including the synthetic integration runs, are in `runs/ledger.jsonl`. No
  failed runs were dropped.
* Nothing committed to git. The preregistration is not frozen.
