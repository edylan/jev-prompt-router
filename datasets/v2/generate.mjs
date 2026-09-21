// Prompt Splitter — dataset v2 generator.
//
// Goals (see ../../docs/dataset-review.md):
//   - template-level, stratified dev/test split (no template spans the split)
//   - no padding artifacts in the canonical prompt (v1's Context suffix and the
//     5-way qualifier are gone)
//   - slots vary setting/surface only and are drawn independently of tier
//   - governance generated independently of capability tier
//   - a harness-realistic slice alongside the business prose
//   - a balanced benchmark: 232 business rows per tier + 72 harness rows = 1000
//   - validation: leakage, duplicates, and tier/governance independence
//
// Usage: node generate.mjs
import fs from 'node:fs';
import path from 'node:path';
import { bankNew, SLOTS } from './bank-new.mjs';
import { bankNew2 } from './bank-new2.mjs';
import { harnessScenarios, harnessFrames, REPOS, MODELS } from './harness-bank.mjs';

const HERE = path.dirname(new URL(import.meta.url).pathname);
const V1_BANK = JSON.parse(fs.readFileSync(path.join(HERE, 'bank-v1.json'), 'utf8'));
const TIERS = ['T0', 'T1', 'T2', 'T3'];
const TIER_TARGET = { T0: 232, T1: 232, T2: 232, T3: 232 };
const SEED = 0x5eed2026;
const MAX_VARIANTS = 20;

// ---------------------------------------------------------------- deterministic RNG
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function hash(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
const makeRng = (key) => mulberry32((SEED ^ hash(key)) >>> 0);
const draw = (rng, arr) => arr[Math.floor(rng() * arr.length)];
const norm = (s) => s.toLowerCase().replace(/[^a-z0-9 ]/g, '').replace(/\s+/g, ' ').trim();

// ---------------------------------------------------------------- metadata
const TASK_FAMILY = {
  email_communication: 'communication_drafting', meetings_collaboration: 'meeting_synthesis',
  documents_summaries: 'document_synthesis', presentations: 'presentation_creation',
  marketing_content: 'content_creation', sales_customer_support: 'customer_revenue_work',
  classification_extraction: 'classification_extraction', data_spreadsheets: 'data_analysis',
  market_competitive_research: 'research_analysis', business_strategy: 'strategy_planning',
  product_design: 'product_definition', software_engineering: 'software_delivery',
  it_security_admin: 'systems_security', people_finance_legal_ops: 'corporate_operations',
  agent_harness: 'software_delivery',
};
const PROFILES = {
  T0: { reasoning_depth: 'low', risk: 'low', context_load: 'small' },
  T1: { reasoning_depth: 'low_to_moderate', risk: 'low_to_medium', context_load: 'small_to_medium' },
  T2: { reasoning_depth: 'moderate_to_high', risk: 'medium', context_load: 'medium_to_large' },
  T3: { reasoning_depth: 'high', risk: 'high', context_load: 'large_or_complex' },
};

function businessFunction(category, core) {
  if (category === 'software_engineering' || category === 'agent_harness') return 'engineering';
  if (category === 'it_security_admin') return 'it_security';
  if (category === 'product_design') return 'product';
  if (category === 'marketing_content') return 'marketing';
  if (category === 'market_competitive_research') return 'research_insights';
  if (category === 'business_strategy') return 'executive_strategy';
  if (category === 'sales_customer_support') return /support|ticket|escalation|churn|customer/i.test(core) ? 'customer_support' : 'sales';
  if (category === 'data_spreadsheets') return /financial|budget|revenue|accounting|ERP|invoice|margin/i.test(core) ? 'finance' : 'analytics';
  if (category === 'classification_extraction') {
    if (/support|customer message/i.test(core)) return 'customer_support';
    if (/expense|invoice|amount/i.test(core)) return 'finance';
    if (/contract|obligation|policy|regulat/i.test(core)) return 'legal_compliance';
    if (/job title|role hierarchy/i.test(core)) return 'people_hr';
    return 'operations';
  }
  if (category === 'people_finance_legal_ops') {
    if (/employee|hiring|workforce|compensation|performance|job description|restructuring/i.test(core)) return 'people_hr';
    if (/finance|financial|accounting|revenue|budget|cash|expense/i.test(core)) return 'finance';
    if (/legal|regulat|counsel|investigation|contract|policy|obligation/i.test(core)) return 'legal_compliance';
    return 'operations';
  }
  if (['email_communication', 'meetings_collaboration', 'documents_summaries', 'presentations'].includes(category)) {
    if (/contract|legal|regulat|counsel|vendor agreement|policy|obligation/i.test(core)) return 'legal_compliance';
    if (/employee|hiring|workforce|performance|training/i.test(core)) return 'people_hr';
    if (/revenue|financial|finance|budget|expense|invoice|quarter/i.test(core)) return 'finance';
    if (/customer|buyer|sales|CRM|product demo/i.test(core)) return /support|training/i.test(core) ? 'customer_support' : 'sales';
    if (/campaign|marketing|LinkedIn|landing page|positioning/i.test(core)) return 'marketing';
    if (/board|leadership|acquisition|strategy|executive/i.test(core)) return 'executive_strategy';
    return category === 'meetings_collaboration' ? 'operations' : 'general_administration';
  }
  return 'operations';
}

// Governance drawn independently of tier, so capability and policy are separate axes.
function governanceFor(rng) {
  const s = rng();
  const data_sensitivity = s < 0.5 ? 'low' : s < 0.82 ? 'moderate' : 'high';
  const regulated_domain = rng() < 0.3;
  const r = rng();
  const data_residency_requirement = r < 0.5 ? 'unspecified' : r < 0.7 ? 'EU' : r < 0.9 ? 'US' : 'APAC';
  return {
    data_sensitivity,
    regulated_domain,
    cloud_processing_allowed: data_sensitivity === 'high' ? 'policy_check_required' : 'yes',
    data_residency_requirement,
    vendor_allowlist_required: regulated_domain || data_sensitivity === 'high',
  };
}

const STYLE_DIRECTIVES = [
  null, null, 'Use plain language and mark any assumptions.',
  'Be concise, but do not omit material caveats.',
  'If information is missing, list it instead of inventing it.',
  'Return the result in a format I can paste into our working document.',
];
const REQUESTER_CONTEXTS = [
  null, null, 'The requester is a {role} at a {industry} company.',
  'This is blocking a decision due next week.', 'The result will be shared with {audience}.',
];
function ambientFor(rng) {
  const style = draw(rng, STYLE_DIRECTIVES);
  let context = draw(rng, REQUESTER_CONTEXTS);
  if (context) context = context.replace('{role}', draw(rng, SLOTS.role)).replace('{industry}', draw(rng, SLOTS.industry)).replace('{audience}', draw(rng, SLOTS.audience));
  return { style_directive: style, requester_context: context };
}

function renderTemplate(template, rng) {
  return template.replace(/\{(\w+)\}/g, (_, slot) => {
    if (!SLOTS[slot]) throw new Error(`Unknown slot {${slot}}`);
    return draw(rng, SLOTS[slot]);
  });
}

// ---------------------------------------------------------------- build deduped template set
const seenTemplates = new Set();
const templates = []; // {key, category, tier, source, split, template}
let tplCounter = 0;
function addTemplate(category, tier, source, template) {
  const n = norm(template);
  if (seenTemplates.has(n)) return;
  seenTemplates.add(n);
  templates.push({ key: `${category}|${tier}|${source}|t${tplCounter++}`, category, tier, source, template });
}
for (const category of Object.keys(V1_BANK.bank)) {
  for (const tier of TIERS) (V1_BANK.bank[category]?.[tier] ?? []).forEach((e) => addTemplate(category, tier, 'v1', e.template));
}
for (const bank of [bankNew, bankNew2]) {
  for (const category of Object.keys(bank)) {
    for (const tier of TIERS) (bank[category]?.[tier] ?? []).forEach((t) => addTemplate(category, tier, 'new', t));
  }
}
// stratified split at the template level: every 5th template in a (category,tier) bucket -> dev
const bucketIndex = {};
for (const t of templates) {
  const b = `${t.category}|${t.tier}`;
  bucketIndex[b] = (bucketIndex[b] ?? -1) + 1;
  t.split = bucketIndex[b] % 5 === 0 ? 'development' : 'test';
  t.variants = (() => {
    const out = []; const seen = new Set();
    const hasSlots = /\{\w+\}/.test(t.template);
    for (let v = 0; v < (hasSlots ? MAX_VARIANTS : 1); v++) {
      const core = renderTemplate(t.template, makeRng(`${t.key}#${v}`)).replace(/\s+/g, ' ').trim();
      if (seen.has(core)) continue;
      seen.add(core); out.push(core);
    }
    return out;
  })();
}

// ---------------------------------------------------------------- balanced allocation
const usedPrompts = new Set();
const selected = []; // {tpl, core, variant}
for (const tier of TIERS) {
  const inTier = templates.filter((t) => t.tier === tier);
  const target = TIER_TARGET[tier];
  outer: for (let v = 0; v < MAX_VARIANTS; v++) {
    for (const tpl of inTier) {
      if (selected.filter((s) => s.tpl.tier === tier).length >= target) break outer;
      const core = tpl.variants[v];
      if (!core) continue;
      const n = norm(core);
      if (usedPrompts.has(n)) continue;
      usedPrompts.add(n);
      selected.push({ tpl, core, variant: v });
    }
  }
}

const businessRows = selected.map(({ tpl, core, variant }) => {
  const rng = makeRng(`row#${tpl.key}#${variant}`);
  const gov = governanceFor(rng);
  const { style_directive, requester_context } = ambientFor(rng);
  return {
    prompt_style: 'business',
    category: tpl.category,
    business_function: businessFunction(tpl.category, core),
    task_family: TASK_FAMILY[tpl.category],
    template_key: tpl.key,
    template_source: tpl.source,
    split: tpl.split,
    prompt: core,
    style_directive,
    requester_context,
    prompt_with_ambient: [core, style_directive, requester_context].filter(Boolean).join(' '),
    gold_tier: tpl.tier,
    label_status: 'synthetic_prior',
    labeling_rule: 'minimum_sufficient_capability',
    rubric_version: 'v2',
    ...PROFILES[tpl.tier],
    tools_or_attachments_implied: /supplied|attached|transcript|workbook|logs|code|reports|documents|thread|filings|spreadsheets|source|artifact/i.test(core),
    required_modalities: ['text'],
    governance: gov,
    vendor_preference: null,
  };
});

// ---------------------------------------------------------------- harness slice
const harnessRows = [];
for (const tier of TIERS) {
  harnessScenarios[tier].forEach((scenario, idx) => {
    const scenarioKey = `harness|${tier}|${idx}`;
    const split = idx % 5 === 0 ? 'development' : 'test';
    for (const [harness, render] of Object.entries(harnessFrames)) {
      const rng = makeRng(`${scenarioKey}#${harness}`);
      const prompt = render({ turn: 1 + Math.floor(rng() * 6), repo: draw(rng, REPOS), model: draw(rng, MODELS), request: scenario.request, signals: scenario.signals });
      harnessRows.push({
        prompt_style: 'harness', harness, turn_shape: scenario.shape, category: 'agent_harness',
        business_function: 'engineering', task_family: 'software_delivery', template_key: scenarioKey,
        template_source: 'harness', split, prompt, style_directive: null, requester_context: null,
        prompt_with_ambient: prompt, gold_tier: tier, label_status: 'synthetic_prior',
        labeling_rule: 'minimum_sufficient_capability', rubric_version: 'v2', ...PROFILES[tier],
        tools_or_attachments_implied: true, required_modalities: ['text'],
        governance: governanceFor(makeRng(`gov#${scenarioKey}#${harness}`)), vendor_preference: null,
      });
    }
  });
}

// ---------------------------------------------------------------- ids & ordering
const shuffle = (arr, rng) => { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const rngAll = makeRng('order');
const business = shuffle(businessRows, rngAll).map((r, i) => ({ id: `biz-${String(i + 1).padStart(4, '0')}`, ...r }));
const harness = shuffle(harnessRows, rngAll).map((r, i) => ({ id: `har-${String(i + 1).padStart(4, '0')}`, ...r }));
const all = [...business, ...harness];

// ---------------------------------------------------------------- validation
const counts = (rows, key) => Object.fromEntries(Object.entries(rows.reduce((a, r) => { a[r[key]] = (a[r[key]] ?? 0) + 1; return a; }, {})).sort());
function cramersV(rows, aFn, bFn) {
  const aVals = [...new Set(rows.map(aFn))];
  const bVals = [...new Set(rows.map((r) => String(bFn(r))))];
  const n = rows.length;
  const obs = aVals.map(() => bVals.map(() => 0));
  for (const r of rows) obs[aVals.indexOf(aFn(r))][bVals.indexOf(String(bFn(r)))] += 1;
  const rowT = obs.map((row) => row.reduce((x, y) => x + y, 0));
  const colT = bVals.map((_, j) => obs.reduce((s, row) => s + row[j], 0));
  let chi2 = 0;
  for (let i = 0; i < aVals.length; i++) for (let j = 0; j < bVals.length; j++) {
    const e = (rowT[i] * colT[j]) / n;
    if (e > 0) chi2 += (obs[i][j] - e) ** 2 / e;
  }
  return Math.sqrt(chi2 / (n * Math.min(aVals.length - 1, bVals.length - 1)));
}
const devT = new Set(templates.filter((t) => t.split === 'development').map((t) => t.key));
const testT = new Set(templates.filter((t) => t.split === 'test').map((t) => t.key));
const overlap = [...devT].filter((k) => testT.has(k));
const businessTemplates = new Set(business.map((r) => r.template_key));
const dupCores = business.length - new Set(business.map((r) => norm(r.prompt))).size;
const tierGovTable = {};
for (const t of TIERS) {
  const sub = business.filter((r) => r.gold_tier === t);
  tierGovTable[t] = {
    n: sub.length,
    high_sensitivity: +(sub.filter((r) => r.governance.data_sensitivity === 'high').length / sub.length).toFixed(3),
    moderate_sensitivity: +(sub.filter((r) => r.governance.data_sensitivity === 'moderate').length / sub.length).toFixed(3),
    regulated: +(sub.filter((r) => r.governance.regulated_domain).length / sub.length).toFixed(3),
    policy_check: +(sub.filter((r) => r.governance.cloud_processing_allowed !== 'yes').length / sub.length).toFixed(3),
  };
}

const manifest = {
  schema_version: 2,
  generated_at: new Date().toISOString().slice(0, 10),
  seed: `0x${SEED.toString(16)}`,
  rubric_version: 'v2',
  counts: {
    business: business.length, harness: harness.length, total: all.length,
    business_templates: businessTemplates.size,
    business_rows_per_template: +(business.length / businessTemplates.size).toFixed(2),
    by_tier: counts(all, 'gold_tier'), by_split: counts(all, 'split'),
    business_by_tier: counts(business, 'gold_tier'), business_by_split: counts(business, 'split'),
    business_by_category: counts(business, 'category'), business_by_function: counts(business, 'business_function'),
    harness_by_tier: counts(harness, 'gold_tier'), harness_by_harness: counts(harness, 'harness'),
  },
  integrity: {
    templates_spanning_split: overlap.length,
    dev_templates: devT.size, test_templates: testT.size,
    duplicate_canonical_prompts: dupCores,
    harness_scenarios_spanning_split: 0,
  },
  independence: {
    note: 'Governance and ambient fields are deliberately drawn independently of gold_tier. Cramers V near 0 = independent.',
    cramers_v_tier_vs_data_sensitivity: +cramersV(business, (r) => r.gold_tier, (r) => r.governance.data_sensitivity).toFixed(4),
    cramers_v_tier_vs_regulated_domain: +cramersV(business, (r) => r.gold_tier, (r) => r.governance.regulated_domain).toFixed(4),
    cramers_v_tier_vs_residency: +cramersV(business, (r) => r.gold_tier, (r) => r.governance.data_residency_requirement).toFixed(4),
    tier_governance_table: tierGovTable,
  },
  warning: 'gold_tier is a synthetic prior, not empirical proof of model adequacy.',
};

// ---------------------------------------------------------------- write
const jl = (rows) => rows.map((r) => JSON.stringify(r)).join('\n') + '\n';
fs.writeFileSync(path.join(HERE, 'business-prompts-v2.jsonl'), jl(business));
fs.writeFileSync(path.join(HERE, 'harness-prompts-v2.jsonl'), jl(harness));
fs.writeFileSync(path.join(HERE, 'all-prompts-v2.jsonl'), jl(all));
const csvEscape = (v) => `"${String(v).replaceAll('"', '""')}"`;
const cols = ['id', 'split', 'prompt_style', 'category', 'business_function', 'task_family', 'template_source', 'prompt', 'gold_tier', 'label_status', 'reasoning_depth', 'risk', 'context_load', 'tools_or_attachments_implied', 'governance'];
fs.writeFileSync(path.join(HERE, 'business-prompts-v2.csv'), [cols.join(','), ...business.map((r) => cols.map((c) => csvEscape(typeof r[c] === 'object' && r[c] !== null ? JSON.stringify(r[c]) : r[c])).join(','))].join('\n') + '\n');
fs.writeFileSync(path.join(HERE, 'manifest-v2.json'), JSON.stringify(manifest, null, 2) + '\n');

console.log(JSON.stringify(manifest.counts, null, 2));
console.log('integrity:', JSON.stringify(manifest.integrity));
console.log('independence:', JSON.stringify(manifest.independence, null, 1));
