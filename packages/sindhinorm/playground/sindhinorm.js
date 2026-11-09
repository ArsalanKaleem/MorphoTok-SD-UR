// sindhinorm.js: JavaScript port of sindhinorm/core.py (same rules, same outputs).
// Parity with the Python package is checked by playground/parity_test.mjs.
(function (root) {
  "use strict";
  const ZWNJ = "‌", ZWJ = "‍";
  const CLASSES = {
    "ي": "yeh", "ی": "yeh", "ى": "yeh", "ے": "yeh",
    "ه": "heh", "ھ": "heh", "ہ": "heh",
    "ڪ": "kaf", "ک": "kaf", "ك": "kaf",
  };
  const MEMBERS = {
    yeh: ["ي", "ی", "ى", "ے"],
    heh: ["ه", "ھ", "ہ"],
    kaf: ["ڪ", "ک", "ك"],
  };
  const LEXICAL = new Set(["ڪ", "ک", "ك", "ے"]);
  const SAFE_OOV = { "ی": "ي", "ى": "ي", "ہ": "ه" };
  const MAX_CANDIDATES = 4096;
  const NATIVE_KEEP_LIST = [
    ["جے", "جي"], ["ڪي", "کي"], ["کے", "کي"], ["کی", "کي"], ["ڪان", "کان"], ["تہ", "ته"],
    ["تھ", "ته"], ["کري", "ڪري"], ["كيو", "ڪيو"], ["کيو", "ڪيو"], ["ہے", "هي"], ["کئی", "ڪئي"],
    ["كئي", "ڪئي"], ["کئي", "ڪئي"], ["ڪيس", "کيس"], ["شاھھ", "شاهه"], ["کن", "ڪن"], ["كن", "ڪن"],
    ["ڪجھھ", "ڪجهه"], ["ڪجھہ", "ڪجهه"], ["ڪجهھ", "ڪجهه"], ["ڏڪڻ", "ڏکڻ"], ["کو", "ڪو"], ["کيل", "ڪيل"],
  ];
  const keyOf = (a, b) => a + "\u0000" + b;
  const NATIVE_KEEP = new Set(NATIVE_KEEP_LIST.map(([a, b]) => keyOf(a, b)));

  const WORD_RE = /^[\p{L}\p{M}]$/u;
  const MN_RE = /^\p{Mn}$/u;
  const isWordChar = (c) => WORD_RE.test(c);

  function cleanZeroWidth(text) {
    const t = Array.from(text);
    const out = [];
    let i = 0;
    const n = t.length;
    while (i < n) {
      const c = t[i];
      if (c !== ZWNJ && c !== ZWJ) { out.push(c); i++; continue; }
      let j = i;
      while (j < n && (t[j] === ZWNJ || t[j] === ZWJ)) j++;
      const run = t.slice(i, j);
      const left = out.length ? out[out.length - 1] : "";
      const right = j < n ? t[j] : "";
      if (left && right && isWordChar(left) && isWordChar(right) && run.includes(ZWNJ)) {
        if (!MN_RE.test(left) && !MN_RE.test(right)) out.push(ZWNJ);
      }
      i = j;
    }
    return out.join("");
  }

  function tokens(text) {
    const t = Array.from(text);
    const res = [];
    let buf = [];
    let word = null;
    for (let i = 0; i < t.length; i++) {
      const c = t[i];
      const inside = isWordChar(c) ||
        (c === ZWNJ && buf.length > 0 && word === true && i + 1 < t.length && isWordChar(t[i + 1]));
      const w = !!inside;
      if (word === null || w === word) buf.push(c);
      else { res.push([word, buf.join("")]); buf = [c]; }
      word = w;
    }
    if (buf.length) res.push([!!word, buf.join("")]);
    return res;
  }

  class Normalizer {
    constructor(lexicon, opts = {}) {
      this.lexicon = lexicon instanceof Map ? lexicon : new Map(Object.entries(lexicon));
      this.lexRatio = opts.lexRatio ?? 50;
      this.lexMaxCount = opts.lexMaxCount ?? 100;
      this.keep = opts.keep ?? NATIVE_KEEP;
      this.cache = new Map();
    }
    count(w) { return this.lexicon.get(w) || 0; }
    candidates(word) {
      const slots = Array.from(word).map((c) => (c in CLASSES ? MEMBERS[CLASSES[c]] : [c]));
      if (slots.filter((s) => s.length > 1).length > 8) return [word];
      const out = [];
      const idx = new Array(slots.length).fill(0);
      // itertools.product order: the last slot changes fastest
      while (out.length < MAX_CANDIDATES) {
        out.push(idx.map((k, p) => slots[p][k]).join(""));
        let p = slots.length - 1;
        while (p >= 0) {
          idx[p]++;
          if (idx[p] < slots[p].length) break;
          idx[p] = 0;
          p--;
        }
        if (p < 0) break;
      }
      return out;
    }
    isLexical(word, cand) {
      const a = Array.from(word), b = Array.from(cand);
      for (let k = 0; k < a.length; k++) {
        if (a[k] !== b[k] && (LEXICAL.has(a[k]) || LEXICAL.has(b[k]))) return true;
      }
      return false;
    }
    allowed(word, cand) {
      if (cand === word || this.keep.has(keyOf(word, cand))) return false;
      const fw = this.count(word), fc = this.count(cand);
      if (fc <= fw) return false;
      if (this.isLexical(word, cand)) return fw <= this.lexMaxCount && fc >= this.lexRatio * Math.max(fw, 1);
      return true;
    }
    decide(word) {
      if (!Array.from(word).some((c) => c in CLASSES)) return [word, "no-variant-letters"];
      const ranked = this.candidates(word)
        .map((c, k) => [c, this.count(c), k])
        .sort((x, y) => y[1] - x[1] || x[2] - y[2])
        .map((x) => x[0]);
      const best = ranked.find((c) => this.allowed(word, c)) ?? word;
      if (best !== word) return [best, this.isLexical(word, best) ? "lexical-merge" : "encoding-merge"];
      const fw = this.count(word);
      if (fw === 0) {
        const folded = Array.from(word).map((c) => SAFE_OOV[c] ?? c).join("");
        if (folded !== word && !this.keep.has(keyOf(word, folded))) return [folded, "unknown-fold"];
      }
      const top = ranked.find((c) => c !== word && this.count(c) > fw);
      if (top !== undefined) return [word, this.keep.has(keyOf(word, top)) ? "native-keep" : "lexical-guard"];
      return [word, fw === 0 ? "unknown-kept" : "already-canonical"];
    }
    normalizeWord(word) {
      if (!this.cache.has(word)) this.cache.set(word, this.decide(word)[0]);
      return this.cache.get(word);
    }
    normalize(text) {
      const t = cleanZeroWidth(text.normalize("NFC"));
      return tokens(t).map(([isW, w]) => (isW ? this.normalizeWord(w) : w)).join("");
    }
    explain(text) {
      const t = cleanZeroWidth(text.normalize("NFC"));
      const out = [];
      for (const [isW, w] of tokens(t)) {
        if (!isW) continue;
        const [o, rule] = this.decide(w);
        out.push({ word: w, output: o, rule, count_in: this.count(w), count_out: this.count(o) });
      }
      return out;
    }
  }

  const api = { ZWNJ, ZWJ, CLASSES, MEMBERS, LEXICAL, SAFE_OOV, NATIVE_KEEP, NATIVE_KEEP_LIST, keyOf,
    isWordChar, cleanZeroWidth, tokens, Normalizer };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.sindhinorm = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
