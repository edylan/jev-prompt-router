// Harness-realistic scenarios: what a network interceptor actually sees from
// agent harnesses (Claude Code, Codex, pi). Rendered by generate.mjs, one row
// per (scenario, harness).
export const REPOS = ['acme/checkout-api', 'acme/web-app', 'acme/data-pipeline', 'acme/identity', 'acme/billing-worker', 'internal/platform', 'internal/admin-ui'];
export const MODELS = ['claude-sonnet-4-5', 'gpt-5-codex', 'claude-opus-4-1', 'gemini-2.5-pro', 'qwen3-coder'];

export const harnessScenarios = {
  T0: [
    { request: 'Rename the `usr` variable to `user` in src/auth/session.ts and fix the two call sites.', signals: 'files: src/auth/session.ts (142 lines)', shape: 'single' },
    { request: 'Add a docstring and one usage example to the exported function in src/utils/retry.ts.', signals: 'files: src/utils/retry.ts (58 lines)', shape: 'single' },
    { request: 'Fix the typo in the README install command so it matches the actual package name.', signals: 'files: README.md', shape: 'single' },
    { request: 'Add an aria-label to the icon-only button in src/components/IconButton.tsx.', signals: 'files: src/components/IconButton.tsx', shape: 'single' },
    { request: 'Convert src/lib/legacy.cjs from CommonJS to ESM and update the one importer.', signals: 'files: src/lib/legacy.cjs, src/index.ts', shape: 'single' },
    { request: 'Update the default request timeout constant from 30000 to 15000 and note it in the changelog.', signals: 'files: src/config/defaults.ts, CHANGELOG.md', shape: 'single' },
  ],
  T1: [
    { request: 'Add pagination to the /api/projects endpoint, following the pattern used by /api/users, and add tests.', signals: 'files: src/api/projects.ts, src/api/users.ts, tests/api/users.test.ts', shape: 'multi' },
    { request: 'Write a migration adding a nullable archived_at column and backfill it for rows where status = archived.', signals: 'files: db/migrations/, src/models/project.ts', shape: 'multi' },
    { request: 'Update the Dockerfile to node:20-alpine and make sure the production build still passes.', signals: 'files: Dockerfile, .github/workflows/ci.yml', shape: 'multi' },
    { request: 'Add request validation to the signup handler using the existing zod schemas, with tests for each failure case.', signals: 'files: src/routes/signup.ts, src/schemas/*.ts', shape: 'multi' },
    { request: 'Split src/services/reporting.ts (600 lines) into three modules without changing behavior.', signals: 'files: src/services/reporting.ts, tests/services/reporting.test.ts', shape: 'multi' },
    { request: 'Fix the lint errors reported in CI and add the missing rule to the shared config.', signals: 'files: .eslintrc.cjs, 14 reported files', shape: 'tool-loop' },
  ],
  T2: [
    { request: 'CI is failing only on the concurrency job. Find why the integration tests are flaky and fix it deterministically.', signals: 'files: tests/integration/*.test.ts, .github/workflows/ci.yml; failing run attached', shape: 'tool-loop' },
    { request: 'Implement an audit log across the API, database, and admin UI, following existing repository patterns and preserving backward compatibility.', signals: 'files: src/api/**, db/schema.sql, internal/admin-ui/**', shape: 'multi' },
    { request: 'This React list re-renders on every keystroke. Profile it and fix the performance regression without changing behavior.', signals: 'files: src/components/SearchableList.tsx, src/hooks/useFilter.ts', shape: 'tool-loop' },
    { request: 'Refactor the billing module into testable components without changing public behavior, with an incremental migration plan.', signals: 'files: src/services/billing.ts (612 lines), tests/billing/*.test.ts', shape: 'multi' },
    { request: 'Add OpenTelemetry tracing to the request path and a test asserting the expected spans are emitted.', signals: 'files: src/middleware/**, tests/observability/**', shape: 'multi' },
    { request: 'Implement a per-tenant rate limiter backed by Redis, with tests for burst and sustained traffic.', signals: 'files: src/middleware/rateLimit.ts, docker-compose.yml', shape: 'multi' },
  ],
  T3: [
    { request: 'Production is returning duplicate charges for a subset of customers. Logs, retries, and a recent migration are all suspects. Find the most likely causal chain and a safe recovery plan.', signals: 'services: payments-api, billing-worker; 40k log lines attached; recent migration: 20240612_add_ledger.sql', shape: 'tool-loop' },
    { request: 'Design and implement a cross-repo feature spanning the API, a Go worker, and the web app, with migration tooling, observability, and a staged rollout.', signals: 'repos: acme/checkout-api, acme/billing-worker, acme/web-app', shape: 'multi' },
    { request: 'Design a zero-downtime migration from a single Postgres primary to a sharded setup without losing ordering guarantees.', signals: 'files: db/schema.sql, docs/architecture.md; traffic: 3k writes/s', shape: 'multi' },
    { request: 'Our auth service was flagged in a security review. Audit the session lifecycle across application code and infrastructure, and produce concrete patches plus adversarial tests.', signals: 'files: src/auth/**, infra/terraform/**, security-review.pdf attached', shape: 'tool-loop' },
    { request: 'Two services believe they own the same customer record and both write to it. Design a resolution that preserves existing clients and prevents split-brain updates.', signals: 'services: crm-sync, identity; shared table: customers', shape: 'multi' },
    { request: 'A distributed workflow leaves inconsistent state when a step times out after its side effect commits. Make it idempotent and recoverable, and prove it with failure-injection tests.', signals: 'files: src/workflows/**, tests/fault-injection/**', shape: 'multi' },
  ],
};

const frame = (harness, o) =>
  `[${harness}] turn=${o.turn} cwd=${o.repo} requested_model=${o.model} tools=[${o.tools}]\n[context] ${o.signals}\n[user] ${o.request}`;

export const harnessFrames = {
  'claude-code': (o) => frame('claude-code', { ...o, tools: 'Read,Edit,Write,Bash,Grep,Glob' }),
  codex: (o) => frame('codex', { ...o, tools: 'shell,apply_patch,read_file,list_dir' }),
  pi: (o) => frame('pi', { ...o, tools: 'read,bash,edit,write,grep,find' }),
};
