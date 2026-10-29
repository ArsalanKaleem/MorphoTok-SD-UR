# Raw data provenance

## wikipedia_20231101/

| File | Source URL | Retrieved | Bytes | SHA-256 |
|---|---|---|---|---|
| `wiki_sd.parquet` | https://huggingface.co/datasets/wikimedia/wikipedia/resolve/main/20231101.sd/train-00000-of-00001.parquet | 2026-10-29 | 17,591,997 | `67b17451643c47490951c74a7c2865d86df248500f3f293c0fdc91c0810e763b` |
| `wiki_ur.parquet` | https://huggingface.co/datasets/wikimedia/wikipedia/resolve/main/20231101.ur/train-00000-of-00001.parquet | 2026-10-29 | 167,627,869 | `f711c56af77a88ea8036282c9c49243d0319fe0ddf08ea4e88800d0482d6f8d0` |

* **Dataset:** `wikimedia/wikipedia` on Hugging Face, Wikipedia dump of 2023-11-01,
  configs `20231101.sd` and `20231101.ur`. Rows have `id`, `url`, `title`, `text`.
* **Licence (as stated on the dataset card):** CC BY-SA 3.0 and GFDL. Redistribution
  of derived text must keep attribution and share-alike terms. The files are not
  committed (`.gitignore`).
* **Not verified:** how the dataset card's text was extracted from wikitext (the card does
  not say), and whether every page is in the stated language. `prepare_wikipedia.py`
  applies an Arabic-*script* filter, not language identification.
* **Not usable for:** Leipzig Corpora Collection pages are behind an anti-bot challenge and
  were not accessed.

Derived pilot files are in `data/processed/` with a `*.manifest.json` each (parameters,
filter counts, input and output SHA-256).

## fineweb2/ (web domain)

| File | Source | Bytes | SHA-256 |
|---|---|---|---|
| `snd_Arab_test.parquet` | https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/resolve/main/data/snd_Arab/test/000_00000.parquet | 4,581,430 | `4fe15758d83a7ef39fd801b4f2d499ddae9b16210a44abb45d9ffff2e36b10d4` |
| `urd_Arab_test.parquet` | https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/resolve/main/data/urd_Arab/test/000_00000.parquet | 71,344,862 | `277ecdeebc1b9327a684243897afc3a8acd1a44774b5c6cc67afc6899298e058` |

Retrieved 2026-10-29. Licence: ODC-By 1.0 per the dataset card; Common Crawl terms of use
also apply. Only the *test* split was used (the train shards are 0.4 GB for Sindhi and 6.9 GB for Urdu).

## ud/ (Universal Dependencies treebanks; manual lemmas)

| File(s) | Source | SHA-256 |
|---|---|---|
| `sd_isra-ud-{train,dev,test}.conllu` | github.com/UniversalDependencies/UD_Sindhi-Isra (master; train via raw.githubusercontent.com, dev/test via cdn.jsdelivr.net) | see below |
| `ur_udtb-ud-{train,dev,test}.conllu` | github.com/UniversalDependencies/UD_Urdu-UDTB (master, via cdn.jsdelivr.net mirror) | see below |

Full hashes: sd train `a321069b0337fc12078f5c44df7166068d7fa82aeed3a3c0b55b416d00dfa49c`, dev
`8f24e20b04c7595ac00b529eebb1c3af9fe0663bba910fc1cddf4695bcc3c16e`, test
`ea1128ea255365a449cae5f27ef88ac6fcde392df52bc005213aa7c680edc4c6`; ur train
`08445e961f7960db938a447df2ff902755cae0a6605201264a2eacd3d5475f99`, dev
`0d8ac3c4f8838ea3fe05a6a3028ce4bcd187a505225a2fd2e6f43084bc2e86e1`, test
`b47c89659bfafd5219d859aa47f78e34877a0eb350a17ab9834a78b045f45f58`. File sizes match the
GitHub API listing. Licences (copied as `UD_*.LICENSE.txt`): Sindhi-Isra **CC BY-SA 4.0**
(newswire, folk stories; Bauer et al., UDW 2025); Urdu-UDTB **CC BY-NC-SA 4.0**
(non-commercial: research use only).

## unimorph/

`urd.tsv` from https://raw.githubusercontent.com/unimorph/urd/master/urd (685,613 bytes,
`3a3129d858c7c02d0ec5c8971f5b60842813dbe2513efaf7effd22842dcff4a3`). 12,572 (lemma, form,
features) rows, 182 lemmas. Licence CC BY-SA 3.0 (UniMorph project, as listed by the
`unimorph/universal_morphologies` dataset script; not re-checked on the repo itself).

## zia2018/ (human ZWNJ sub-word annotation)

`data_diacritized.txt` from github.com/harisbinzia/Urdu-Word-Segmentation `Data/` (via
cdn.jsdelivr.net; 993,008 bytes,
`bde7eea3097ada3ef87f3ae589dcbc75a7b5e8d0aca1de98048f81dbbe87216d`) and its `LICENSE`
(CC BY 4.0 legal text; README: "Data licensed under CC-BY 4.0"). Zia, Raza & Athar,
COLING 2018. About 111k tokens with ZWNJ at sub-word boundaries.
