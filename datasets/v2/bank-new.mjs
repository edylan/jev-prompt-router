// New v2 business scenarios (100), added on top of the 194 extracted from v1.
// Templates use {slot} tokens. Slots are setting/surface variation only and are
// drawn independently of tier, so they never signal capability.
export const SLOTS = {
  company: ['Northstar Logistics', 'Cedar Health', 'Aperture Labs', 'Harbor & Finch', 'Brightline Energy', 'Juniper Retail', 'Atlas Foods', 'Clearwater Financial', 'Redwood Manufacturing', 'Beacon Learning'],
  industry: ['B2B software', 'healthcare operations', 'specialty retail', 'logistics', 'financial services', 'manufacturing', 'professional services', 'consumer subscriptions', 'education technology', 'renewable energy'],
  audience: ['the executive team', 'a skeptical CFO', 'regional managers', 'prospective customers', 'the board', 'new employees', 'enterprise buyers', 'nontechnical stakeholders'],
  region: ['North America', 'the UK and Ireland', 'Southeast Asia', 'DACH', 'Australia and New Zealand', 'the US Midwest'],
  product: ['inventory planning platform', 'employee scheduling app', 'expense-management service', 'telehealth portal', 'warehouse analytics product', 'customer-support suite', 'procurement marketplace', 'learning-management platform'],
  stack: ['TypeScript and PostgreSQL', 'Python and FastAPI', 'React and Node.js', 'Go and Redis', 'Ruby on Rails', 'Kubernetes on AWS', 'Next.js and Supabase'],
  tone: ['warm and concise', 'direct but diplomatic', 'confident without sounding promotional', 'plainspoken and professional', 'friendly and action-oriented'],
  system: ['the billing service', 'the identity service', 'the notification worker', 'the reporting API', 'the ingestion pipeline', 'the payments gateway', 'the search indexer', 'the export job', 'the webhook dispatcher', 'the schedule optimizer', 'the recommendation engine', 'the audit logger'],
  artifact: ['vendor proposal', 'security questionnaire', 'RFP response', 'statement of work', 'implementation plan', 'data-processing agreement', 'board memo', 'incident report', 'supplier agreement', 'migration plan'],
  deliverable: ['a decision memo', 'a one-page brief', 'an executive summary', 'a structured comparison', 'a recommendation with options', 'an action plan', 'a risk register'],
  role: ['an operations director', 'a finance manager', 'a support lead', 'a security engineer', 'a product manager', 'a regional sales lead', 'a compliance officer', 'a data analyst', 'a procurement manager', 'a people partner'],
  source: ['the attached transcript', 'the supplied workbook', 'the vendor response', 'the internal policy', 'the customer thread', 'the audit findings', 'the research notes', 'the usage data'],
  uiElement: ['buttons', 'menu items', 'tooltips', 'form fields', 'error banners', 'dialogs', 'empty-state messages', 'table headers'],
  metric: ['gross margin', 'churn rate', 'daily active users', 'on-time delivery', 'conversion rate', 'support backlog', 'inventory turns', 'cash runway', 'net revenue retention', 'cycle time'],
  col: ['C', 'D', 'E', 'F', 'G'],
  field: ['invoice number', 'renewal date', 'account owner', 'cost center', 'tax id', 'contract term', 'payment terms', 'region'],
  n: ['10', '12', '15', '20', '25', '30', '40', '50', '60'],
  formatA: ['MM/DD/YYYY', 'DD/MM/YYYY', 'YYYY/MM/DD', 'Unix timestamps'],
  formatB: ['ISO 8601', 'YYYY-MM-DD', 'UTC dates'],
  doc: ['policy', 'procedure', 'project brief', 'meeting summary', 'one-page memo', 'release note'],
  channel: ['email', 'Slack message', 'LinkedIn post', 'internal announcement', 'support macro', 'newsletter'],
  event: ['office closure', 'system maintenance', 'product launch', 'policy change', 'quarterly review', 'hiring freeze'],
  items: ['support tickets', 'survey comments', 'expense entries', 'leads', 'invoices', 'job applicants'],
  lang: ['TypeScript', 'Python', 'Go', 'Java', 'Ruby', 'SQL'],
  errorType: ['null reference', 'timeout', 'permission denied', 'rate limit', 'syntax', 'connection refused'],
  flow: ['signup', 'password reset', 'checkout', 'onboarding', 'refund', 'invoice approval'],
  artifactType: ['vendor proposal', 'security questionnaire', 'RFP response', 'statement of work', 'implementation plan', 'data-processing agreement', 'board memo', 'incident report'],
  assetType: ['case study', 'product announcement', 'launch email', 'webinar invite', 'one-pager', 'customer story'],
  inputType: ['meeting notes', 'support transcripts', 'project updates', 'interview summaries', 'field reports'],
  planType: ['content plan', 'launch plan', 'enablement plan', 'retention plan', 'hiring plan'],
  docType: ['landing page', 'product brief', 'campaign brief', 'launch FAQ', 'positioning memo'],
  recordType: ['support tickets', 'expense entries', 'leads', 'invoices', 'survey responses', 'job titles'],
  schema: ['CRM', 'finance', 'HRIS', 'analytics'],
  workbookType: ['KPI workbook', 'monthly finance pack', 'sales forecast', 'pipeline report'],
  moduleType: ['reporting', 'billing', 'ingestion', 'notification', 'auth'],
  featureType: ['pagination', 'filtering', 'search', 'audit logging', 'retries', 'rate limiting'],
  bugType: ['duplicate-job', 'timeout', 'memory leak', 'race condition', 'flaky test', 'stale cache'],
  modelType: ['budget model', 'forecast model', 'pricing model', 'capacity model', 'retention model'],
  interviewType: ['user interviews', 'customer interviews', 'stakeholder interviews', 'support calls'],
  systems: ['AWS', 'GitHub', 'the production database', 'Kubernetes', 'Okta', 'Snowflake', 'Terraform'],
  systemA: ['the billing service', 'the identity service', 'the notification worker', 'the reporting API', 'the ingestion pipeline'],
  systemB: ['the payments gateway', 'the search indexer', 'the export job', 'the webhook dispatcher', 'the schedule optimizer'],
  targetArchitecture: ['a sharded setup', 'a multi-region active-active setup', 'a new managed service', 'a partitioned event log'],
  capability: ['regulatory reporting', 'on-call coverage', 'customer data access', 'incident response', 'payments processing'],
  jurisdiction: ['the EU', 'the UK', 'Germany', 'France', 'Australia', 'Brazil'],
  sourceA: ['the regulatory consultation', 'the internal policy manual', 'the outside-counsel memo', 'the vendor contract', 'the audit findings'],
  sourceB: ['the customer thread', 'the market report', 'the incident review', 'the diligence memo'],
  threatType: ['supply-chain compromise', 'credential stuffing', 'insider exfiltration', 'ransomware', 'API key leak'],
  surfaceA: ['CI', 'package registries', 'cloud identities', 'production workloads'],
  surfaceB: ['the admin console', 'the identity provider', 'the data warehouse', 'the edge network'],
  account: ['a strategic enterprise account', 'a top-10 account', 'a regulated banking customer', 'a global logistics customer'],
  market: ['the European market', 'the SMB segment', 'the healthcare vertical', 'Southeast Asia', 'the mid-market'],
  workflow: ['clinical intake', 'procurement approval', 'revenue reconciliation', 'employee onboarding', 'incident triage'],
  contractType: ['multi-year SaaS contract', 'professional-services agreement', 'usage-based contract', 'reseller agreement'],
  meetingType: ['leadership', 'board', 'steering-committee', 'planning'],
};

export const bankNew = {
  business_strategy: {
    T0: [
      'Write a one-line objective and two measurable key results for each priority in this list, using only the numbers provided.',
      'Group these supplied initiatives under the four approved themes and flag any that do not fit any theme.',
      'Rewrite these objectives so each begins with a verb and contains exactly one metric, without changing their meaning.',
    ],
    T1: [
      'Turn the {source} and the two attached spreadsheets into {deliverable} covering variances, risks, and the decisions still needed.',
      'Use the supplied hypotheses and interview notes to list which assumptions are now supported, which are weakened, and what evidence is missing.',
    ],
    T2: [
      'Evaluate three supplied expansion markets for {company} using the attached unit economics, and recommend a sequencing with leading indicators and stop conditions.',
    ],
    T3: [
      'Two business units report the same metric differently and each claims the higher figure. Using the supplied definitions, reconciliation notes, and board correspondence, determine the defensible number, document the discrepancy, and state what must change to prevent recurrence.',
      'Assess whether to wind down a declining product line whose customers depend on it for a regulated workflow. Use the supplied churn, support, and contractual data to model the financial, legal, and reputational consequences, and recommend a staged plan with decision gates.',
    ],
  },
  classification_extraction: {
    T0: [],
    T1: [
      'Normalize these 80 job titles into the supplied 12-role hierarchy, following the mapping rules and flagging any title that plausibly fits two roles.',
      'Extract the notice period, renewal date, liability cap, and governing law from each of these 30 contract summaries into one JSON schema, using null when a field is absent.',
    ],
    T2: [
      'Classify 300 inbound procurement requests against the supplied 25-category taxonomy, return the top two labels with an evidence phrase for each, and route anything below the stated confidence to review.',
    ],
    T3: [
      'Build a stable taxonomy for these 8,000 unlabeled operational requests, balancing durable categories against emerging themes, and specify migration rules from the legacy labels.',
      'Resolve a corporate ownership graph across multilingual filings, renamed subsidiaries, and joint ventures. Cite the source for every edge and mark uncertain relationships explicitly.',
      'Determine whether these 400 incident reports describe one recurring failure or several distinct ones, given inconsistent naming and overlapping symptoms. Produce groupings with the supporting evidence and the alternative interpretations that remain open.',
      'Reconcile three incompatible product taxonomies from acquired companies into one extensible schema, preserving the mappings needed to keep historical reporting comparable.',
    ],
  },
  data_spreadsheets: {
    T0: [
      'Write a formula that flags a row when the invoice date is more than 30 days before the payment date and the amount exceeds 10,000.',
    ],
    T1: [
      'Turn the {source} into a column-by-column cleaning plan with validation rules, deduplication logic, and the exceptions that need a human decision.',
      'Review this KPI workbook and write commentary on material movements, missing periods, and the three figures most likely to be misread.',
    ],
    T2: [
      'Build a driver-based budget model for {company} with assumptions, scenario toggles, and integrity checks that catch broken links and circular references.',
    ],
    T3: [
      'Audit this multi-sheet forecast for inconsistent scenario assumptions, hard-coded overrides, and circular references. Reconstruct the intended logic and rank the corrections by their effect on the decision.',
      'Design a causal analysis plan for a revenue decline using the supplied transaction, pricing, marketing, and support data. Address confounding, missingness, and seasonality, and state what cannot be inferred observationally.',
      'Reconcile results across ERP exports, board packs, and regional spreadsheets that use different currencies, calendars, and recognition rules, and produce an auditable bridge with every adjustment explained.',
    ],
  },
  documents_summaries: {
    T0: [
      'List the deadlines and named owners in this one-page brief, and note anything mentioned without a date.',
    ],
    T1: [
      'Summarize this {artifact} into scope, fees, assumptions, exclusions, timeline, and the questions we still need to ask.',
      'Compare these two internal policies and produce a difference table, without interpreting legal effect.',
    ],
    T2: [
      'Synthesize five customer-interview summaries into themes, counterexamples, and open questions, separating how often something was said from how important it appears to be.',
    ],
    T3: [
      'Reconcile a regulatory consultation, an internal policy manual, and an outside-counsel memo into an obligation matrix with conflicts, jurisdictional caveats, and the questions that require counsel.',
      'Synthesize competing technical and commercial reports into a defensible recommendation that shows how the conclusion changes if the key uncertain assumptions are wrong.',
      'Analyze a large diligence set of contracts, board materials, and operating reports to find contradictions that could materially change the acquisition thesis, citing every finding.',
    ],
  },
  email_communication: {
    T0: [],
    T1: [
      'Draft a customer email explaining a two-week delay, including the revised date, a workaround, and when we will next update them. The tone should be {tone}.',
      'Adapt the same approved announcement for employees and for resellers, changing emphasis and detail for each audience without altering the facts.',
    ],
    T2: [],
    T3: [
      'Given a long thread in which Legal, Sales, and Product disagree about a contractual commitment, reconstruct what was actually decided, identify the contradictions, and draft a reply that resolves the ambiguity without creating a new obligation.',
      'Prepare outage communications for regulated customers in three countries, producing internal, customer, regulator, and public versions that stay factually consistent while meeting different disclosure obligations.',
      'Analyze twenty executive emails about a stalled acquisition, infer each stakeholders unstated concern, and draft a message that moves the group toward a decision without overstating consensus.',
      'Two executives give conflicting accounts of a verbal commitment made to a strategic partner. Using the supplied correspondence and meeting notes, determine the most defensible account and draft a message that protects both the relationship and the company.',
    ],
  },
  it_security_admin: {
    T0: [
      'Write a command that lists the ten largest files under /var/log with human-readable sizes, without deleting anything.',
    ],
    T1: [
      'Create a runbook for rotating a service account credential across CI, staging, and production, with verification and rollback at each step.',
      'Translate this firewall-change request into an implementation checklist covering source, destination, port, owner, test, and expiry.',
    ],
    T2: [
      'Design a least-privilege access model for engineers, support staff, and contractors across AWS, GitHub, and the production database, and state how it would be tested.',
    ],
    T3: [
      'Investigate a suspected supply-chain compromise spanning CI, package registries, cloud identities, and production workloads. Build competing hypotheses, an evidence-preserving containment plan, and explicit recovery gates.',
      'Redesign the security architecture of a multi-tenant regulated platform after two near misses, integrating threat modeling, identity boundaries, data isolation, and operational feasibility.',
      'Plan recovery from a regional cloud failure combined with corrupted backups and uncertain replication state, prioritizing data integrity over superficial availability and stating what must be verified before service is restored.',
    ],
  },
  market_competitive_research: {
    T0: [
      'Build a comparison table from these five competitor descriptions using pricing, target customer, and deployment model.',
      'Summarize these two market notes and list the points where they disagree.',
    ],
    T1: [
      'Create structured competitor profiles from the supplied pages and review excerpts, clearly separating stated facts from interpretation.',
      'Build a market-sizing worksheet from the supplied customer counts and spending assumptions, showing low, base, and high cases.',
    ],
    T2: [
      'Assess the competitive landscape for {product} in {region}, segmenting competitors by business model and buyer, distinguishing sourced facts from inference, and naming the evidence gaps.',
    ],
    T3: [
      'Form an investment-grade market thesis from conflicting analyst reports, primary interviews, public filings, and incomplete private-company data. Quantify the uncertainty and design the tests that would disconfirm it.',
      'Analyze how a major regulatory change could reshape the competitive structure of {industry} over five years, modeling second-order effects, strategic responses, and alternative scenarios.',
      'Determine whether an apparent new category is durable or merely a feature bundle, integrating product architecture, buyer behavior, unit economics, and competitor incentives.',
    ],
  },
  marketing_content: {
    T0: [
      'Write five short social captions announcing a webinar for {product}, avoiding emojis and exaggerated claims.',
    ],
    T1: [
      'Write a landing-page draft for {product} using the supplied positioning, proof points, and prohibited-claims list.',
      'Adapt this approved case study into a short email, a one-pager, and three social posts without adding results we cannot support.',
    ],
    T2: [
      'Develop messaging pillars for {product} across three buyer roles, giving each role a problem, a promise, a proof point, and an objection response.',
    ],
    T3: [
      'Reposition a mature product whose category is commoditizing. Using the supplied win/loss research, roadmap, and competitor claims, propose a defensible category narrative and identify the claims we cannot support.',
      'Design a global launch narrative that must work across materially different regulatory and cultural contexts while remaining one coherent brand, and surface where localization requires product changes rather than copy changes.',
      'A campaign performed well on reach but poorly on qualified pipeline. Using the supplied channel, creative, and sales-feedback data, determine the most likely cause, distinguish it from measurement error, and recommend what to change.',
      'Reconcile a brand team that wants premium positioning with a sales team that needs a price-led message for a price-sensitive segment. Produce a recommendation that preserves margin and states what evidence would settle the dispute.',
    ],
  },
  meetings_collaboration: {
    T0: [
      'Turn this transcript excerpt into five bullets covering decisions, owners, and dates, and mark any owner who was not explicitly named.',
    ],
    T1: [
      'Summarize a 45-minute project meeting into decisions, action items, owners, dependencies, and open questions.',
      'Combine two consecutive planning meetings into one status record, preserving changed dates and superseded decisions.',
    ],
    T2: [
      'Summarize a 90-minute cross-functional meeting, separating firm decisions from proposals and assumptions, and flag where participants appear to disagree about what was decided.',
    ],
    T3: [
      'Synthesize six months of leadership transcripts into a map of recurring unresolved decisions, shifting assumptions, and commitments that were made but never closed, citing the meeting and speaker for every conclusion.',
      'Two teams give incompatible accounts of the same steering-committee decision. Reconstruct the most defensible version, identify what each side omits, and specify what must be confirmed before work continues.',
      'Analyze a merger-integration workshop with conflicting stakeholder accounts and produce the operating decision that is most defensible, together with the conditions that must hold for it to remain valid.',
      'Review a year of board minutes and identify decisions that quietly reversed earlier ones, including who drove the change and what was never formally recorded. Cite the minutes for each finding.',
    ],
  },
  people_finance_legal_ops: {
    T0: [
      'Turn these expense-policy bullets into a short employee FAQ with one question per bullet.',
    ],
    T1: [
      'Create a hiring scorecard for an operations manager from the supplied role brief, including competencies, interview questions, and anchored rating guidance.',
      'Summarize this monthly finance pack into actual-versus-budget movements, cash concerns, and questions for budget owners.',
    ],
    T2: [
      'Design a vendor-selection process with weighted criteria, conflict-of-interest controls, a pilot design, and a defensible decision record.',
    ],
    T3: [
      'Model a restructuring that must cut cost while preserving critical capabilities, meeting jurisdiction-specific consultation duties, and avoiding hidden single points of failure. Provide scenarios for leadership and questions for counsel.',
      'Assess whether to recognize revenue on a complex multi-year contract with variable consideration, implementation obligations, and side letters. Present the competing interpretations and the evidence each one requires.',
    ],
  },
  presentations: {
    T0: [
      'Rewrite these slide titles so each states the takeaway rather than the topic.',
    ],
    T1: [
      'Turn this five-page memo into an eight-slide presentation with takeaway titles, concise body copy, and speaker notes.',
      'Improve this existing deck by removing repetition, fixing the narrative order, and proposing one visual per slide.',
    ],
    T2: [
      'Create a 12-slide investor-update narrative from the supplied metrics that leads with the central tension, specifies each chart, and does not hide the missed target.',
    ],
    T3: [
      'Design a board deck for a choice among three acquisition targets using incomplete and partly contradictory diligence. Build the argument, the sensitivity cases, the decision gates, and the appendix structure.',
      'Create an executive presentation on a four-business-unit restructuring that balances financial necessity, employee impact, operational dependencies, and legal uncertainty without false precision.',
      'Turn a mixed set of spreadsheets, interviews, and market reports into a strategy deck with an auditable claim-to-source map and explicit alternative interpretations.',
    ],
  },
  product_design: {
    T0: [
      'Rewrite these error messages so each says what happened and what to do next, in one sentence.',
      'Create a short QA checklist for a password-reset flow, listing every state a user can reach.',
    ],
    T1: [
      'Turn these customer requests into a scoped feature brief with problem statement, primary user, workflow, acceptance criteria, analytics, and non-goals.',
      'Create an interview guide to test whether finance managers understand and trust an automated reconciliation feature.',
    ],
    T2: [
      'Prioritize this roadmap using customer value, strategic fit, evidence strength, engineering cost, and reversibility, and explain the close calls.',
    ],
    T3: [
      'Define a new 0-to-1 product for an underserved workflow using fragmented research. Produce the opportunity thesis, system model, wedge, principles, failure modes, and validation sequence.',
      'Redesign a mature platforms information architecture while preserving compatibility for three distinct user groups and hundreds of integrations, and provide the migration strategy and decision framework.',
      'Determine whether repeated customer requests represent one extensible platform capability or several incompatible vertical products, using product, architecture, and go-to-market evidence.',
    ],
  },
  sales_customer_support: {
    T0: [
      'Classify each of these support requests as billing, technical, account access, or feature request, and draft a one-line acknowledgment for each.',
    ],
    T1: [
      'Draft a response to a frustrated customer whose issue needed three handoffs, acknowledging the experience and describing the concrete recovery steps.',
      'Create a discovery-call question set for {role} evaluating {product}, organized by workflow, impact, decision process, and timing.',
    ],
    T2: [
      'Create a negotiation plan for a renewal where usage grew 40%, the customer wants flat pricing, and a competitor has offered a migration credit.',
    ],
    T3: [
      'Develop an enterprise account strategy from two years of calls, tickets, product usage, org changes, and contract history. Model stakeholder incentives and identify the most credible expansion path and its failure modes.',
      'Analyze a threatened strategic-account churn involving product gaps, executive turnover, and disputed service credits, and produce recovery options with their commercial, legal, and operational tradeoffs.',
      'Two regions report contradictory win/loss reasons for the same product. Using the supplied CRM notes, call recordings, and pricing history, determine what is actually driving losses and what the data cannot support.',
      'A key customer claims a verbal promise of a capability we do not sell. Reconstruct what was likely said across the account history and recommend a response that preserves the relationship without conceding the obligation.',
    ],
  },
  software_engineering: {
    T0: [
      'Write a function that deduplicates a list of objects by id, keeping the first occurrence, and include three tests.',
    ],
    T1: [
      'Implement pagination, filtering, and sorting on this existing endpoint, following the repository pattern and adding unit tests.',
      'Write a migration for {stack} that adds a nullable status column, backfills it in batches, and includes a safe rollback.',
    ],
    T2: [],
    T3: [
      'Trace a production data-corruption bug across {system} using partial logs, retries, asynchronous consumers, and a recent schema migration. Identify the most plausible causal chain and a safe recovery plan.',
      'Evaluate three competing architectures for a globally distributed collaboration product, reasoning about consistency, latency, conflict resolution, operability, and migration from the current system.',
    ],
  },
};
