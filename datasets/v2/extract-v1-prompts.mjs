// Extract the 194 v1 scenarios into a clean, tokenized template bank.
// - removes the fabricated " Context: ..." suffix
// - removes the 5-way qualifier padding (the leaky artifact)
// - re-tokenizes substituted entities so v2 can re-draw them
// Usage: node extract-v1-prompts.mjs [path-to-v1.jsonl]
import fs from 'node:fs';
import path from 'node:path';

const HERE = path.dirname(new URL(import.meta.url).pathname);
const V1 = process.argv[2] || '/home/dylan/Development/chronocle/tmp/jev-router-eval/business-prompts-1000.jsonl';
const OUT = path.join(HERE, 'bank-v1.json');

const companies = ['Northstar Logistics', 'Cedar Health', 'Aperture Labs', 'Harbor & Finch', 'Brightline Energy', 'Juniper Retail', 'Atlas Foods', 'Clearwater Financial', 'Redwood Manufacturing', 'Beacon Learning'];
const industries = ['B2B software', 'healthcare operations', 'specialty retail', 'logistics', 'financial services', 'manufacturing', 'professional services', 'consumer subscriptions', 'education technology', 'renewable energy'];
const audiences = ['the executive team', 'a skeptical CFO', 'regional managers', 'prospective customers', 'the board', 'new employees', 'enterprise buyers', 'nontechnical stakeholders'];
const regions = ['North America', 'the UK and Ireland', 'Southeast Asia', 'DACH', 'Australia and New Zealand', 'the US Midwest'];
const products = ['inventory planning platform', 'employee scheduling app', 'expense-management service', 'telehealth portal', 'warehouse analytics product', 'customer-support suite', 'procurement marketplace', 'learning-management platform'];
const stacks = ['TypeScript and PostgreSQL', 'Python and FastAPI', 'React and Node.js', 'Go and Redis', 'Ruby on Rails', 'Kubernetes on AWS', 'Next.js and Supabase'];
const tones = ['warm and concise', 'direct but diplomatic', 'confident without sounding promotional', 'plainspoken and professional', 'friendly and action-oriented'];

const QUALIFIERS = [
  '',
  'Use plain language and clearly mark any assumptions.',
  'Return the result in a format I can paste directly into our working document.',
  'Be concise, but do not omit material caveats.',
  'If information is missing, list it instead of inventing it.',
];

const subs = [
  ...companies.map((v) => [v, '{company}']),
  ...industries.map((v) => [v, '{industry}']),
  ...audiences.map((v) => [v, '{audience}']),
  ...regions.map((v) => [v, '{region}']),
  ...products.map((v) => [v, '{product}']),
  ...stacks.map((v) => [v, '{stack}']),
  ...tones.map((v) => [v, '{tone}']),
].sort((a, b) => b[0].length - a[0].length);

const tokenize = (text) => subs.reduce((acc, [from, to]) => acc.split(from).join(to), text);

const rows = fs.readFileSync(V1, 'utf8').trim().split('\n').map((l) => JSON.parse(l));
const groups = new Map();
for (const r of rows) {
  const key = `${r.category}\u0000${r.gold_tier}\u0000${r.task_variant}`;
  if (!groups.has(key)) groups.set(key, []);
  groups.get(key).push(r);
}

const bank = {};
let count = 0;
const issues = [];
for (const [key, rs] of [...groups.entries()].sort()) {
  const [category, tier, variant] = key.split('\u0000');
  let p = rs[0].prompt;
  p = p.replace(/\s*Context: The requester works at[\s\S]*$/, '').trim();
  for (const q of QUALIFIERS) {
    if (q && p.endsWith(q)) p = p.slice(0, -q.length).trim();
  }
  if (/Context:|requester works at/.test(p)) issues.push({ key, residue: p.slice(-80) });
  p = tokenize(p).replace(/\s+/g, ' ').trim();
  ((bank[category] ??= {})[tier] ??= []).push({ template: p, source: 'v1', v1_variant: Number(variant) });
  count += 1;
}

for (const c of Object.keys(bank)) {
  for (const t of Object.keys(bank[c])) {
    bank[c][t].sort((a, b) => a.v1_variant - b.v1_variant);
  }
}

fs.writeFileSync(OUT, JSON.stringify({ source: V1, extracted: count, issues, bank }, null, 2) + '\n');
console.log(JSON.stringify({ extracted: count, issues: issues.length, categories: Object.keys(bank).length, out: OUT }, null, 2));
if (issues.length) console.log('RESIDUE:', JSON.stringify(issues.slice(0, 10), null, 2));
