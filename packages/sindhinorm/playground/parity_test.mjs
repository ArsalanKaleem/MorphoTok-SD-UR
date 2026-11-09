// node parity_test.mjs CASES.json LEXICON.json.gz : compare sindhinorm.js with the Python package.
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { Normalizer } = require("./sindhinorm.js");
const [casesPath, lexPath] = process.argv.slice(2);
const cases = JSON.parse(readFileSync(casesPath, "utf8"));
const norm = new Normalizer(JSON.parse(gunzipSync(readFileSync(lexPath)).toString("utf8")));
let bad = 0;
for (const [w, out, rule] of cases.words) {
  const [o, r] = norm.decide(w);
  if (o !== out || r !== rule) { if (bad++ < 5) console.log("word", JSON.stringify([w, out, rule, o, r])); }
}
for (const [t, out, expl] of cases.texts) {
  const o = norm.normalize(t);
  const e = JSON.stringify(norm.explain(t));
  if (o !== out || e !== JSON.stringify(expl)) { if (bad++ < 10) console.log("text", JSON.stringify([t, out, o])); }
}
console.log(`${cases.words.length} words, ${cases.texts.length} texts, mismatches: ${bad}`);
process.exit(bad ? 1 : 0);
