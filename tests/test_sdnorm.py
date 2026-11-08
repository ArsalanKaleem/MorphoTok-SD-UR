"""Unit tests for the sdnorm Sindhi normalizer (hand-built lexicon, no corpus)."""

from collections import Counter

from morphtok.tools.sdnorm import ZWJ, ZWNJ, Normalizer, build_lexicon, clean_zero_width

LEX = Counter({"آهي": 30000, "آھي": 9000, "جي": 170000, "کي": 47000, "ڪي": 2000, "کی": 160,
               "ڪتاب": 6000, "کتاب": 13, "ڪري": 19000, "کري": 14, "ته": 22000, "تہ": 5000,
               "اسلام": 900, "آباد": 3000})  # fmt: skip


def norm() -> Normalizer:
    return Normalizer(LEX.copy())


def test_encoding_variant_goes_to_most_frequent() -> None:
    assert norm().normalize_word("آھي") == "آهي"
    assert norm().normalize_word("جی") == "جي"  # unseen variant of a frequent word


def test_two_real_words_are_not_merged() -> None:
    assert norm().normalize_word("ڪي") == "ڪي"  # some vs to: ratio too small


def test_rare_keyboard_variant_of_lexical_letter_is_merged() -> None:
    assert norm().normalize_word("کتاب") == "ڪتاب"


def test_native_keep_pairs_are_respected() -> None:
    assert norm().normalize_word("کری") != "کي"
    assert norm().normalize_word("کی") == "کی"  # Urdu "of": native DIFFERENT
    assert norm().normalize_word("کري") == "کري"  # native DIFFERENT although rare
    assert norm().normalize_word("تہ") == "تہ"


def test_unknown_word_gets_only_safe_folds() -> None:
    assert norm().normalize_word("زمیںک") == "زميںک"  # ی folded, ک untouched


def test_zero_width_cleanup() -> None:
    assert clean_zero_width("اسلام" + ZWNJ + "آباد") == "اسلام" + ZWNJ + "آباد"
    assert clean_zero_width("آهي" + ZWNJ + " ") == "آهي "
    assert clean_zero_width("رح" + ZWJ * 3 + ZWNJ + " x") == "رح x"
    assert clean_zero_width(ZWNJ + "آباد") == "آباد"


def test_normalize_text_keeps_punctuation_and_spaces() -> None:
    assert norm().normalize("هي ڪتاب آھي، " + "کتاب.") == "هي ڪتاب آهي، ڪتاب."


def test_build_lexicon_counts_words() -> None:
    lex = build_lexicon(["آهي آهي، ڪتاب" + ZWNJ + " "])
    assert lex["آهي"] == 2 and lex["ڪتاب"] == 1
