// Second batch of v2 scenarios: slot-rich templates that each yield many
// distinct, tier-neutral variants. Used to balance the benchmark across tiers.
export const bankNew2 = {
  product_design: {
    T0: [
      'Rewrite the labels on these {uiElement} so each is clear and consistent in under eight words.',
      'Create a {n}-item QA checklist for the {flow} flow.',
    ],
    T1: [
      'Create a {n}-question discovery guide for {role} evaluating {product}.',
    ],
    T2: [
      'Synthesize {n} {interviewType} into jobs, pains, and opportunity areas, preserving contradictory segments rather than forcing one persona.',
    ],
    T3: [
      'Define a 0-to-1 product for the {workflow} workflow using fragmented research, with an opportunity thesis, wedge, principles, failure modes, and validation sequence.',
    ],
  },
  data_spreadsheets: {
    T0: [
      'Write a {lang} formula that flags a row when {metric} falls below the target in column {col}.',
      'Convert these {formatA} dates into {formatB}.',
      'Write a SQL query that returns {metric} by region for the last {n} days.',
    ],
    T1: [
      'Review this {workbookType} and write commentary on material movements and the figures most likely to be misread.',
    ],
    T2: [
      'Build a driver-based {modelType} for {company} with assumptions, scenario toggles, and integrity checks that catch broken links.',
    ],
  },
  classification_extraction: {
    T0: [
      'Extract the {field} from each of these {n} short records into a single CSV.',
      'Classify each of these {n} {items} into the three categories supplied, and return one label per row.',
    ],
    T1: [
      'Normalize these {n} {recordType} into the supplied {schema} schema, using null when a field is missing.',
    ],
  },
  documents_summaries: {
    T0: [
      'Summarize this {doc} in three bullets for {audience}.',
      'Turn these {n} bullets into a numbered checklist, keeping the original order.',
      'Fix the grammar and punctuation in this {doc} without changing its meaning.',
      'Rewrite this {doc} so a new employee can follow it, keeping every step in order.',
    ],
    T1: [
      'Summarize this {artifactType} into {deliverable} covering scope, fees, assumptions, exclusions, and open questions.',
    ],
    T3: [
      'Reconcile {sourceA}, {sourceB}, and the board minutes into an obligation matrix with conflicts, jurisdictional caveats, and questions for counsel.',
    ],
  },
  marketing_content: {
    T0: [
      'Draft a {n}-word {channel} about the {event}.',
    ],
    T1: [
      'Adapt the approved {assetType} for {audience} and {audience} without changing the facts.',
      'Build a {n}-month {planType} for {audience} covering channels, owners, and review points.',
      'Write a {docType} for {product} using the supplied positioning, proof points, and prohibited claims.',
    ],
    T3: [
      'Reposition a mature {product} whose category is commoditizing, using win/loss research and competitor claims, and identify the claims we cannot support.',
    ],
  },
  software_engineering: {
    T0: [
      'Add a docstring and one usage example to the {lang} function below.',
      'Explain this {errorType} message and name the first thing to check.',
    ],
    T1: [
      'Split this {moduleType} module into focused files without changing behavior, and add tests for the extracted parts.',
      'Implement {featureType} on this endpoint following the existing repository pattern, with tests.',
    ],
    T2: [
      'Diagnose the intermittent {bugType} in {system} from the supplied code and logs, and propose a minimal fix with tests and rollout safeguards.',
      'Refactor the {moduleType} module into testable components without changing public behavior, with an incremental migration plan.',
    ],
    T3: [
      'Trace a production data-corruption bug across {systemA} and {systemB} using partial logs, retries, and a recent migration. Identify the most plausible causal chain and a safe recovery plan.',
      'Design a zero-downtime migration of {systemA} to {targetArchitecture} without losing ordering guarantees.',
    ],
  },
  meetings_collaboration: {
    T1: [
      'Turn these {n} {inputType} into {deliverable} with owners, dates, and dependencies.',
    ],
    T3: [
      'Synthesize six months of {meetingType} meetings into recurring unresolved decisions and commitments that were never closed, citing speaker and date.',
    ],
  },
  sales_customer_support: {
    T3: [
      'Develop an enterprise account strategy for {account} from two years of calls, tickets, and contract history. Model stakeholder incentives and failure modes.',
    ],
  },
  it_security_admin: {
    T1: [
      'Translate this change request for {systems} into an implementation checklist with source, destination, owner, test, and rollback.',
    ],
    T2: [
      'Design a least-privilege access model for {role} across {systems}, and state how it would be tested.',
    ],
    T3: [
      'Investigate a suspected {threatType} spanning {surfaceA} and {surfaceB}. Build competing hypotheses and an evidence-preserving containment plan.',
    ],
  },
  market_competitive_research: {
    T2: [
      'Assess the competitive landscape for {product} in {region}, separating sourced facts from inference and naming the evidence gaps.',
    ],
    T3: [
      'Form an investment-grade market thesis for {market} from conflicting analyst reports and incomplete private data, and design the tests that would disconfirm it.',
    ],
  },
  people_finance_legal_ops: {
    T3: [
      'Model a restructuring that must cut cost while preserving {capability}, meeting {jurisdiction} consultation duties, and avoiding hidden single points of failure.',
      'Assess whether to recognize revenue on a {contractType} with variable consideration and side letters, presenting the competing interpretations and the evidence each requires.',
      'Determine whether a proposed {planType} is affordable under three revenue scenarios using the supplied unit economics, and identify the assumptions that would change the decision.',
    ],
  },
  business_strategy: {
    T3: [
      'Reconcile two business units that report {metric} differently and both claim the higher figure. Determine the defensible number and the control that prevents recurrence.',
      'Advise whether {company} should build, buy, or partner for {capability}, weighing control, speed, integration risk, and the scenario in which each choice fails.',
    ],
  },
};
