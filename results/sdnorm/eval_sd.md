# sdnorm evaluation (Sindhi)

Lexicon: sd_wiki20231101_pilot66141.txt (3,534,829 word tokens, 135,483 types). Thresholds fixed before evaluation: lex_ratio = 50, lex_max_count = 100.

## 1. Agreement with native judgements (150 pairs; keep-list disabled)

| | rule merges | rule keeps apart |
|---|---|---|
| native SAME | 125 | 1 |
| native DIFFERENT/UNSURE | 18 | 6 |

Merge precision 0.874, recall 0.992, accuracy 0.873. With the keep-list enabled the DIFFERENT/UNSURE pairs are never merged by construction.

Disagreements:

* sd-V002: جي / جے native KEEP, rule SAME
* sd-V005: کي / کی native KEEP, rule SAME
* sd-V008: کان / ڪان native KEEP, rule SAME
* sd-V009: ته / تہ native KEEP, rule SAME
* sd-V010: ته / تھ native KEEP, rule SAME
* sd-V017: ڪري / کري native KEEP, rule SAME
* sd-V024: ڪيو / كيو native KEEP, rule SAME
* sd-V025: ڪيو / کيو native KEEP, rule SAME
* sd-V049: ڪئي / کئی native KEEP, rule SAME
* sd-V050: ڪئي / كئي native KEEP, rule SAME
* sd-V051: ڪئي / کئي native KEEP, rule SAME
* sd-V074: شاهه / شاھھ native KEEP, rule SAME
* sd-V089: ڪن / كن native KEEP, rule SAME
* sd-V092: سي / سے native SAME, rule KEEP
* sd-V099: ڏکڻ / ڏڪڻ native KEEP, rule SAME
* sd-V108: ڪجهه / ڪجھھ native KEEP, rule SAME
* sd-V109: ڪجهه / ڪجھہ native KEEP, rule SAME
* sd-V110: ڪجهه / ڪجهھ native KEEP, rule SAME
* sd-V144: ڪيل / کيل native KEEP, rule SAME

## 2. Spelling restoration on the UD Sindhi POS test (news domain)

* Confusable-perturbed tokens (ي → ی): 4,511. After sdnorm, identical to the normalized clean token: **0.940**; identical to the original clean token: 0.923.
* Random-letter control: 4,511 tokens; restored 0.004 (expected near 0: the tool should not undo arbitrary edits).
* Clean test tokens changed by sdnorm: 153 of 11,059 (1.383%).

## 3. Effect on the 5,000-line Sindhi Wikipedia pilot

* Word tokens changed: 13,026 of 266,765 (4.88%).
* Word types: 29,797 → 28,471 (-4.45%).
