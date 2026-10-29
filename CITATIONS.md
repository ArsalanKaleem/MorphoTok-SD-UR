# Citations

Policy: this file lists only works **supplied by the project owner** or **verified
against the primary source** (the arXiv abstract page or the ACL Anthology page) by a
named checker on a recorded date. "Verified" means title, authors, venue and year were
read off that page. It does **not** mean the paper's claims were reproduced. Summaries
are paraphrases of the abstract or landing page only.

## Verified references (checked 2026-10-29 by Claude, the AI assistant, via the pages listed)

| Key | Reference | Page checked | Relevance |
|---|---|---|---|
| kudo2018 | Taku Kudo. *Subword Regularization: Improving Neural Network Translation Models with Multiple Subword Candidates.* ACL 2018. | arxiv.org/abs/1804.10959 | Unigram LM, lattice sampling (Objectives A, E) |
| kudo2018sp | Taku Kudo, John Richardson. *SentencePiece: A simple and language independent subword tokenizer and detokenizer for Neural Text Processing.* EMNLP 2018 (demo). | arxiv.org/abs/1808.06226 | Library backend (TODO) |
| sennrich2016 | Rico Sennrich, Barry Haddow, Alexandra Birch. *Neural Machine Translation of Rare Words with Subword Units.* ACL 2016. | arxiv.org/abs/1508.07909 | BPE baseline |
| provilkov2020 | Ivan Provilkov, Dmitrii Emelianenko, Elena Voita. *BPE-Dropout: Simple and Effective Subword Regularization.* ACL 2020. | arxiv.org/abs/1910.13267 | Stochastic BPE (Family E) |
| bostrom2020 | Kaj Bostrom, Greg Durrett. *Byte Pair Encoding is Suboptimal for Language Model Pretraining.* Findings of EMNLP 2020. | arxiv.org/abs/2004.03720 | BPE vs Unigram |
| gronroos2020 | Stig-Arne Grönroos, Sami Virpioja, Mikko Kurimo. *Morfessor EM+Prune: Improved Subword Segmentation with Expectation Maximization and Pruning.* LREC 2020. | aclanthology.org/2020.lrec-1.486 | Closest EM+pruning relative of the lattice trainer; novelty screen for A |
| brahma2025 | Maharaj Brahma, N J Karthika, Atul Singh, Devaraj Adiga, Smruti Bhate, Ganesh Ramakrishnan, Rohit Saluja, Maunendra Sankar Desarkar. *MorphTok: Morphologically Grounded Tokenization for Indian Languages.* TokShop @ ICML 2025. | arxiv.org/abs/2504.10335 | Morphological pre-tokenization + constrained BPE (Hindi, Marathi); novelty screen for A/B |
| vemula2025 | Saketh Reddy Vemula, Sandipan Dandapat, Dipti Misra Sharma, Parameswari Krishnamurthy. *Rethinking Tokenization for Rich Morphology: The Dominance of Unigram over BPE and Morphological Alignment.* arXiv 2508.08424 (2025). | arxiv.org/abs/2508.08424 | Pre-segmentation helps BPE, not Unigram; novelty screen for B |
| arnett2025coling | Catherine Arnett, Benjamin K. Bergen. *Why do language models perform worse for morphologically complex languages?* COLING 2025, pp. 6607–6623. | aclanthology.org/2025.coling-main.441 (via search result) / arxiv.org/abs/2411.14198 | MorphScore; Urdu included (22 languages) |
| arnett2025morph70 | Catherine Arnett, Marisa Hudspeth, Brendan O'Connor. *Evaluating Morphological Alignment of Tokenizers in 70 Languages.* TokShop @ ICML 2025. | arxiv.org/abs/2507.06378 | Alignment explains little downstream variance; paradigm-coherence screen |
| mccarthy2020 | Arya D. McCarthy, Christo Kirov, Matteo Grella, Amrit Nidhi, Patrick Xia, et al. *UniMorph 3.0: Universal Morphology.* LREC 2020. | aclanthology.org/2020.lrec-1.483 | Urdu paradigms (silver supervision) |
| bauer2025 | John Bauer, Sakiina Shah, Muhammad Shaheer, Mir Afza Ahmed Talpur, Zubair Sanjrani, Sarwat Qureshi, Shafi Pirzada, Christopher D. Manning, Mutee U Rahman. *Universal Dependencies for Sindhi.* UDW (SyntaxFest) 2025, pp. 105–118. | aclanthology.org/2025.udw-1.11 | Sindhi treebank (silver supervision, news domain) |
| zia2018 | Haris Bin Zia, Agha Ali Raza, Awais Athar. *Urdu Word Segmentation using Conditional Random Fields (CRFs).* COLING 2018. | arxiv.org/abs/1806.05432 | Human ZWNJ sub-word annotation (gold for compound boundaries) |
| penedo2025 | Guilherme Penedo, Hynek Kydlíček, Vinko Sabolčec, Bettina Messmer, Negar Foroutan, Amir Hossein Kargaran, Colin Raffel, Martin Jaggi, Leandro Von Werra, Thomas Wolf. *FineWeb2: One Pipeline to Scale Them All — Adapting Pre-Training Data Processing to Every Language.* arXiv 2506.20920 (2025). | arxiv.org/abs/2506.20920 | Web-domain corpus |
| ganchev2010 | Kuzman Ganchev, João Graça, Jennifer Gillenwater, Ben Taskar. *Posterior Regularization for Structured Latent Variable Models.* JMLR 11 (2010) 2001–2049. | jmlr.org/papers/volume11/ganchev10a/ganchev10a.pdf (pp. 2006–2009 read) | Objective A is an instance of PR (Prop. 2.1–2.2, Eq. 5, 8) |
| kohonen2010 | Oskar Kohonen, Sami Virpioja, Krista Lagus. *Semi-supervised learning of concatenative morphology.* SIGMORPHON 2010, pp. 78–86. | aclanthology.org/W10-2210 (PDF pp. 78–81 read) | Closest semi-supervised unigram-lexicon segmentation |
| dobler2023 | Konstantin Dobler, Gerard de Melo. *FOCUS: Effective Embedding Initialization for Monolingual Specialization of Multilingual Models.* EMNLP 2023. | arxiv.org/abs/2305.14481 | Embedding init for Gate 5 (`downstream/adapt.py` is NOT FOCUS) |

Datasets used (cited through their papers above, plus): Wikimedia Wikipedia dump 2023-11-01
(`wikimedia/wikipedia` on Hugging Face) and UD_Urdu-UDTB (the treebank README's citation
has not been checked yet; TODO).

## Unverified placeholders (NOT references)

| Placeholder ID | Topic to locate and verify | Needed for |
|---|---|---|
| UNVERIFIED-8 | Constrained conditional models / constraint-driven learning | Further equivalence context (PR already verified) |
| UNVERIFIED-10 | Fast Vocabulary Transfer (FVT) | `downstream/adapt.py` |
| UNVERIFIED-11 | Unicode Standard: ZWNJ/ZWJ semantics, `ArabicShaping.txt`, UAX #15 | Unicode audit |
| UNVERIFIED-13 | Approximate randomization / bootstrap testing in NLP | `eval/stats.py` |
| UNVERIFIED-14 | Rehman et al. (2011), the ZWNJ placement rules used by zia2018 | Interpreting the Zia gold |
| UNVERIFIED-15 | UD_Urdu-UDTB's own citation (Hindi–Urdu treebank papers) | Silver supervision provenance |
| UNVERIFIED-17 | UrduLM (arXiv 2601.17664), seen in search results only | Urdu tokenizer fertility context |
