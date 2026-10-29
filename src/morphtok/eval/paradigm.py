"""Paradigm coherence: is a lemma's stem tokenized the same way in all its forms?

Needs only inflection paradigms (lemma -> forms), not segmentation gold. For a paradigm
with forms ``F`` (format-stripped, single words), the **paradigm stem** ``s`` is the
longest common prefix of ``F``. For each form ``f``:

* ``stem_ok(f)``: ``f == s`` or position ``|s|`` is a token boundary of ``f``;
* ``stem_tokens(f)``: the tokens covering ``f[:|s|]`` (defined only if ``stem_ok``).

Reported (denominators explicit):

* ``stem_boundary_rate`` = #{forms with stem_ok} / #forms (forms longer than the stem
  only, since ``f == s`` is trivially ok);
* ``coherence`` = #{paradigms where every form is stem_ok and all stem_tokens are
  identical} / #paradigms;
* ``mean_stem_variants`` = mean over paradigms of the number of distinct stem
  tokenizations (1.0 = perfectly coherent; forms with stem_ok false count as their own
  variant).

The LCP stem undershoots when stems alternate; such paradigms get short stems (and
are excluded if shorter than ``min_stem``). Relation to existing alignment metrics
(e.g. MorphScore) is noted in docs/novelty_screening.md; novelty is NOT claimed.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Mapping


def common_prefix(words: list[str]) -> str:
    """Longest common prefix of ``words`` (``""`` for an empty list)."""
    if not words:
        return ""
    lo, hi = min(words), max(words)
    i = 0
    while i < len(lo) and lo[i] == hi[i]:
        i += 1
    return lo[:i]


def _boundaries(tokens: list[str]) -> set[int]:
    return set(itertools.accumulate(len(t) for t in tokens[:-1]))


def paradigm_coherence(
    paradigms: Mapping[str, set[str]],
    encode: Callable[[str], list[str]],
    min_forms: int = 2,
    min_stem: int = 2,
) -> dict[str, float | int | None]:
    """Coherence statistics of ``encode`` over ``paradigms`` (see module docstring)."""
    n_par = coherent = 0
    n_forms_long = stem_ok_long = 0
    variants_sum = 0
    for _lemma, forms in sorted(paradigms.items()):
        flist = sorted(forms)
        if len(flist) < min_forms:
            continue
        stem = common_prefix(flist)
        if len(stem) < min_stem:
            continue
        n_par += 1
        stems: set[tuple[str, ...] | tuple[str, str]] = set()
        all_ok = True
        for f in flist:
            toks = encode(f)
            if "".join(toks) != f:
                raise ValueError(f"tokenization of {f!r} does not reconstruct it")
            ok = len(f) == len(stem) or len(stem) in _boundaries(toks)
            if len(f) > len(stem):
                n_forms_long += 1
                stem_ok_long += ok
            if ok:
                acc, cover = 0, []
                for t in toks:
                    if acc >= len(stem):
                        break
                    cover.append(t)
                    acc += len(t)
                stems.add(tuple(cover))
            else:
                all_ok = False
                stems.add(("<nonaligned>", f))
        variants_sum += len(stems)
        if all_ok and len(stems) == 1:
            coherent += 1
    return {
        "n_paradigms": n_par,
        "coherence": coherent / n_par if n_par else None,
        "stem_boundary_rate": stem_ok_long / n_forms_long if n_forms_long else None,
        "n_forms_longer_than_stem": n_forms_long,
        "mean_stem_variants": variants_sum / n_par if n_par else None,
    }
