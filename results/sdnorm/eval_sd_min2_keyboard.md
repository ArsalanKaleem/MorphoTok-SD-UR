# sdnorm evaluation (Sindhi)

Lexicon: sd_wiki20231101_pilot66141.txt (3,461,064 word tokens, 61,718 types). Thresholds fixed before evaluation: lex_ratio = 50, lex_max_count = 100.
Rules: sindhinorm 0.2.0 keyboard mode.

## 1. Agreement with native judgements (150 pairs; keep-list disabled)

| | rule merges | rule keeps apart |
|---|---|---|
| native SAME | 64 | 62 |
| native DIFFERENT/UNSURE | 13 | 11 |

Merge precision 0.831, recall 0.508, accuracy 0.500. With the keep-list enabled the DIFFERENT/UNSURE pairs are never merged by construction.

Disagreements:

* sd-V002: جي / جے native KEEP, rule SAME
* sd-V004: کي / کے native KEEP, rule SAME
* sd-V005: کي / کی native KEEP, rule SAME
* sd-V006: آهي / آھي native SAME, rule KEEP
* sd-V007: هن / ھن native SAME, rule KEEP
* sd-V009: ته / تہ native KEEP, rule SAME
* sd-V011: هڪ / ھڪ native SAME, rule KEEP
* sd-V013: آهي / آھي native SAME, rule KEEP
* sd-V014: آهي / آھی native SAME, rule KEEP
* sd-V016: به / بھ native SAME, rule KEEP
* sd-V017: ڪري / کري native KEEP, rule SAME
* sd-V018: جنهن / جنھن native SAME, rule KEEP
* sd-V019: آهن / آھن native SAME, rule KEEP
* sd-V021: آهي / آھي native SAME, rule KEEP
* sd-V023: نه / نھ native SAME, rule KEEP
* sd-V024: ڪيو / كيو native KEEP, rule SAME
* sd-V025: ڪيو / کيو native KEEP, rule SAME
* sd-V027: هو / ھو native SAME, rule KEEP
* sd-V028: شھر / شهر native SAME, rule KEEP
* sd-V030: پنهنجي / پنھنجي native SAME, rule KEEP
* sd-V032: هي / ھي native SAME, rule KEEP
* sd-V033: هي / ہے native KEEP, rule SAME
* sd-V036: هي / ھی native SAME, rule KEEP
* sd-V037: هو / ھو native SAME, rule KEEP
* sd-V040: انهن / انھن native SAME, rule KEEP
* sd-V042: اهو / اھو native SAME, rule KEEP
* sd-V044: آهن / آھن native SAME, rule KEEP
* sd-V048: جڏهن / جڏھن native SAME, rule KEEP
* sd-V049: ڪئي / کئی native KEEP, rule SAME
* sd-V050: ڪئي / كئي native KEEP, rule SAME
* sd-V051: ڪئي / کئي native KEEP, rule SAME
* sd-V056: ڪنهن / ڪنھن native SAME, rule KEEP
* sd-V057: هو / ھو native SAME, rule KEEP
* sd-V058: آهن / آھن native SAME, rule KEEP
* sd-V061: انهيءَ / انھيءَ native SAME, rule KEEP
* sd-V063: هئي / ھئي native SAME, rule KEEP
* sd-V064: مشهور / مشھور native SAME, rule KEEP
* sd-V067: هئا / ھئا native SAME, rule KEEP
* sd-V068: ڏينهن / ڏينھن native SAME, rule KEEP
* sd-V069: ماڻهو / ماڻھو native SAME, rule KEEP
* sd-V070: اها / اھا native SAME, rule KEEP
* sd-V071: شاهه / شاھه native SAME, rule KEEP
* sd-V073: شاهه / شاھہ native SAME, rule KEEP
* sd-V075: اهي / اھي native SAME, rule KEEP
* sd-V076: هر / ھر native SAME, rule KEEP
* sd-V079: ماڻهن / ماڻھن native SAME, rule KEEP
* sd-V080: هوندو / ھوندو native SAME, rule KEEP
* sd-V082: هئي / ھئي native SAME, rule KEEP
* sd-V084: ٻه / ٻھ native SAME, rule KEEP
* sd-V085: هتي / ھتي native SAME, rule KEEP
* sd-V087: پهرين / پھرين native SAME, rule KEEP
* sd-V089: ڪن / كن native KEEP, rule SAME
* sd-V094: پهريون / پھريون native SAME, rule KEEP
* sd-V096: گهڻو / گھڻو native SAME, rule KEEP
* sd-V101: رهيو / رھيو native SAME, rule KEEP
* sd-V103: الله / اللھ native SAME, rule KEEP
* sd-V104: اهڙي / اھڙي native SAME, rule KEEP
* sd-V105: رهيو / رھيو native SAME, rule KEEP
* sd-V106: ڪجهه / ڪجھه native SAME, rule KEEP
* sd-V112: شاھ / شاه native SAME, rule KEEP
* sd-V115: هيءُ / ھيءُ native SAME, rule KEEP
* sd-V116: هيءُ / ھیءُ native SAME, rule KEEP
* sd-V118: هوندي / ھوندي native SAME, rule KEEP
* sd-V119: رهي / رھي native SAME, rule KEEP
* sd-V125: هيٺ / ھيٺ native SAME, rule KEEP
* sd-V127: گهر / گھر native SAME, rule KEEP
* sd-V134: هئي / ھئي native SAME, rule KEEP
* sd-V137: اهم / اھم native SAME, rule KEEP
* sd-V139: هندستان / ھندستان native SAME, rule KEEP
* sd-V141: وغيره / وغيرھ native SAME, rule KEEP
* sd-V144: ڪيل / کيل native KEEP, rule SAME
* sd-V146: هوندا / ھوندا native SAME, rule KEEP
* sd-V147: ھيو / هيو native SAME, rule KEEP
* sd-V148: ڏانهن / ڏانھن native SAME, rule KEEP
* sd-V150: هنڌ / ھنڌ native SAME, rule KEEP

## 2. Spelling restoration on the UD Sindhi POS test (news domain)

* Confusable-perturbed tokens (ي → ی): 4,511. After sdnorm, identical to the normalized clean token: **0.949**; identical to the original clean token: 0.949.
* Random-letter control: 4,511 tokens; restored 0.003 (expected near 0: the tool should not undo arbitrary edits).
* Clean test tokens changed by sdnorm: 3 of 11,059 (0.027%).

## 3. Effect on the 5,000-line Sindhi Wikipedia pilot

* Word tokens changed: 1,478 of 266,765 (0.55%).
* Word types: 29,797 → 29,449 (-1.17%).

## 4. Clean news text: SiPOS (no keyboard letters in the text)

* Tokens changed: 7 of 293,683 (0.00%); distinct changes: 3.
* Most frequent: چکي → چڪي (4), اعلى → اعلي (2), عظمى → عظمي (1)
