// node parity_test.mjs CASES.json LEXICON.json.gz : compare sindhinorm.js with the Python package
// in every mode written by make_parity_cases.py (keyboard, frequency, keyboard + fold_heh).
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { Normalizer } = require("./sindhinorm.js");
const [casesPath, lexPath] = process.argv.slice(2);
const cases = JSON.parse(readFileSync(casesPath, "utf8"));
const lexicon = new Map(Object.entries(JSON.parse(gunzipSync(readFileSync(lexPath)).toString("utf8"))));
let total = 0;
for (const [name, c] of Object.entries(cases.modes)) {
  const norm = new Normalizer(lexicon, { mode: c.options.mode, foldHeh: Boolean(c.options.fold_heh) });
  let bad = 0;
  for (const [w, out, rule] of c.words) {
    const [o, r] = norm.decide(w);
    if (o !== out || r !== rule) { if (bad++ < 5) console.log(name, "word", JSON.stringify([w, out, rule, o, r])); }
  }
  for (const [t, out, expl] of c.texts) {
    const o = norm.normalize(t);
    const e = JSON.stringify(norm.explain(t));
    if (o !== out || e !== JSON.stringify(expl)) { if (bad++ < 10) console.log(name, "text", JSON.stringify([t, out, o])); }
  }
  console.log(`${name}: ${c.words.length} words, ${c.texts.length} texts, mismatches: ${bad}`);
  total += bad;
}
process.exit(total ? 1 : 0);
