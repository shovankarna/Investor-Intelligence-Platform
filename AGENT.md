# AGENT.md — Instructions for Any Coding Agent Working on This Repo

> Applies to Claude Code, Antigravity, Cursor, Copilot, or any other agent
> touching this codebase. If you are an agent reading this: these rules are
> not suggestions. Read this file in full before writing or modifying any
> code, and re-check it whenever a task touches a topic covered here.

---

## 0. Source-of-truth hierarchy

When documents disagree, this is the order of authority:

1. **PROJECT.md** — what we're building and why. Architecture, tech
   choices, ADRs. If PROJECT.md doesn't say something, it hasn't been
   decided — see §7.
2. **TRACKING.md** — the task breakdown derived from PROJECT.md. It should
   never contradict PROJECT.md; if you find that it does, flag it, don't
   silently pick one.
3. **AGENT.md (this file)** — how to write the code that implements the
   above. Standards, conventions, guardrails.

Never resolve a conflict between these files by guessing. Flag it (see §7)
and keep going with everything else.

---

## 1. Hard constraints — never violate these

These map directly to PROJECT.md's ADRs. They are not style preferences —
violating them produces a system that's wrong, not just inelegant.

| # | Rule | Why |
|---|---|---|
| 1 | Quantitative metrics are read from Postgres only, never answered from vector search. | Embeddings are lossy over arithmetic. |
| 2 | Every row in `financial_metrics` and `chunks` carries `source_file`/`document_id`, `page_number`, and `section_path`. No exceptions, no nullable-and-fill-later. | Citations are a hard product requirement, not a nice-to-have. |
| 3 | Ratios (margins, FCF, D/E, ROE, ROA, YoY growth) are computed in plain Python from stored raw values. Never ask an LLM to calculate them, never persist an LLM's calculation of them. | Zero hallucination risk on pure arithmetic; zero extra LLM calls. |
| 4 | Ingestion is idempotent: upsert on `content_hash` / `(document_id, metric_name)`. Never append-only. | Re-ingestion during development must not create duplicate rows or duplicate vectors. |
| 5 | LLM calls go through OpenRouter only. No local Ollama or other local-LLM code path, even as a "temporary" fallback. | Dev and prod must hit the identical provider — see PROJECT.md ADR-5. |
| 6 | Money values are `NUMERIC`/`Decimal` end to end — database column, Python variable, API response. Never `float`. | Floating-point rounding has no place in financial data. |
| 7 | No paid service is added without it being written into PROJECT.md's tech-stack table first, status "Decided." | The whole point of this project is that it runs free. |
| 8 | Pre-ingestion validation runs before any heavy parsing. PDFs with < 200 chars or forms other than `10-K`, `10-Q`, `20-F` must be rejected with HTTP 422. | Restricts v1 scope to text-based SEC filings; prevents OCR hallucinations. |
| 9 | Metric extraction must be LLM-first with deterministic verification: filter to primary statements, batch into ONE call with unscaled printed values, check verbatim grounding, enforce Python accounting checks with single retry, and scale units in Python. | Prevents LLM arithmetic hallucinations, multi-call rate limits, and silent data corruption. |

If a task seems to require breaking one of these, stop and flag it (§7)
instead of finding a workaround that technically complies.

---

## 2. General coding standards

**Python (backend, ingestion, RAG pipeline)**
- Python 3.11+. Type hints on every function signature — parameters and
  return type. No bare `Any` unless genuinely unavoidable.
- Docstrings on every public function/class: one-line summary, then
  Args/Returns if non-trivial.
- Formatting/linting: `black` + `ruff`. Run both before considering a task
  done.
- Pydantic models for every API request/response body and every LLM
  structured-output schema. Don't hand-parse JSON from an LLM response.
- Prefer small, single-purpose functions over long ones. If a function is
  doing "parse AND extract AND save," split it.

**TypeScript/React (frontend)**
- TypeScript strict mode. No `any`.
- Functional components, hooks — no class components.
- API calls go through a single typed client module, not scattered `fetch`
  calls across components.
- Server-side data fetching (Next.js) preferred over client-side
  `useEffect` fetches wherever the data is needed at render time.

**Both**
- No commented-out code left in a commit. Delete it — git history keeps it.
- No `console.log`/`print` debugging left in committed code.
- No magic numbers without a named constant (e.g. chunk size, top-K, top-N
  values live in a `config.py`/`config.ts`, not inline).

---

## 3. Repository structure

```
/backend
  /app
    /api          # FastAPI route handlers, one file per resource
    /services      # business logic (extraction, ratios, retrieval, router)
    /models        # Pydantic schemas
    /db            # SQLAlchemy models, migrations
    /rag           # chunking, embedding, reranking, hybrid search
    /llm           # OpenRouter client, fallback chain, prompt templates
  /tests
  requirements.txt (or pyproject.toml — pick one, don't mix)
  .env.example
/frontend
  /app             # Next.js App Router pages
  /components
  /lib             # typed API client, utilities
  .env.example
PROJECT.md
TRACKING.md
AGENT.md
```

Don't invent a different top-level layout without updating this section.

---

## 4. Backend / FastAPI rules

**Do**
- One router per resource (`documents.py`, `metrics.py`, `chat.py`), all
  mounted in a central `main.py`.
- Validate uploaded files: PDF only, size limit enforced. Run `validate_upload(path)`
  to verify text density (>= 200 chars) and form type (`10-K`, `10-Q`, `20-F`) before
  initiating ingestion. Return HTTP 422 on failure.
- Return structured error responses (consistent shape: `{detail, code}`),
  not raw stack traces, to the frontend.
- Load the embedding/reranker models once at startup (module-level
  singleton), not per-request — reloading a model per request will kill
  latency and burn Cloud Run compute budget.

**Don't**
- Don't put business logic in route handlers — routes call services, thin
  as possible.
- Don't call OpenRouter directly from a route handler — go through the
  `/llm` client module so the fallback chain and retry logic are applied
  consistently everywhere.
- Don't add new environment variables without adding them to `.env.example`
  with a comment explaining what they're for.

---

## 5. Database / migrations rules

**Do**
- Use a migration tool (Alembic) from the first schema — don't hand-run SQL
  against Supabase and let the schema drift from what's in version control.
- Every migration is additive by default. A destructive change (dropping a
  column/table) requires flagging it (§7) before writing it, not just
  before running it.
- Index what you filter/sort on: GIN index on `tsv_content`, HNSW/IVFFlat
  on `embedding`, index on `(company, fiscal_year)` for the metrics table.

**Don't**
- Don't use `SELECT *` in application code — name columns explicitly, so a
  schema change surfaces as a clear error, not a silent field mismatch.
- Don't write raw string-interpolated SQL. Parameterized queries /
  ORM only — this is a hard rule, not a style preference (SQL injection).
- Don't change a column type or constraint that existing rows depend on
  without a data-migration plan for existing rows.

---

## 6. RAG / ingestion pipeline rules

**Do**
- Keep the table/prose fork at the element level (per Docling's typed
  output) — never re-flatten a parsed document to one string before
  deciding what's a table and what's prose.
- Filter candidate tables for metric extraction down to primary statements
  (Operations/Income, Balance Sheet, Cash Flows) using `section_path` and headings;
  prune footnote and non-primary tables.
- Send all selected primary statements in ONE batched LLM call with unscaled printed values.
- Serialize tables to Markdown when they have a single header row, HTML
  when they have merged/multi-row headers (`rowspan`/`colspan`). Never
  split a table across chunks mid-row.
- Every chunk gets a contextual header (company/fiscal year/section) before
  embedding — this is what makes retrieval precise enough to be useful on
  its own out of context.
- Batch embedding calls (encode a list of chunks at once), not one chunk
  per call, for throughput.

**Don't**
- Don't chunk by fixed character count as the primary strategy — structure
  (headings, then size-cap) comes first.
- Don't skip the reranking step to save latency without measuring whether
  retrieval quality actually holds up without it first.
- Don't invent a different embedding model without updating PROJECT.md's
  tech table — the vector dimension is baked into the `chunks` schema
  (`VECTOR(384)` for `bge-small`), so swapping models is a migration, not a
  one-line change.

---

## 7. Handling ambiguity — the rule that matters most

**When PROJECT.md doesn't specify a detail a task needs (a chunk size, a
retry count, a prompt wording, a UI copy choice): pick a reasonable default,
implement it, and explicitly mark it as an inferred default in your
output/commit message/PR description — do not present it as if it were a
decision that was already made.**

This applies to comments in code, PR descriptions, and any tracking
document you update. The failure mode this rule exists to prevent: a task
list or changelog that reads as fully decided when large parts of it are
actually the agent's own invented specifics, indistinguishable from real
decisions to whoever reads it next.

If the detail is architecturally significant (changes a schema, changes
which provider/service is used, changes what data is exposed externally,
touches anything in §1's hard constraints) — stop and surface it as an open
question rather than choosing silently, even with a label. Small
tuning-type defaults (chunk size, top-K) are fine to pick and label;
architectural choices are not fine to pick alone.

---

## 8. LLM / OpenRouter usage rules

- All calls go through the shared client in `/llm`, which implements the
  fallback chain (see PROJECT.md §5.2) and exponential backoff on 429/5xx.
- Every extraction call uses a Pydantic schema for structured output — no
  "ask the model to output JSON and hope," use the API's structured-output
  feature if the chosen model supports it, and validate the response
  against the schema before it touches the database.
- Require LLM to return printed numbers unscaled; apply unit scaling in Python.
- Every extracted figure must undergo a verbatim grounding check against the source
  table text for its cited page (`verified=True`/`False`).
- Enforce Python Decimal accounting checks on extracted statements (`assets == liabilities + equity`,
  `gross_profit == revenue - COGS`). On failure, retry once with only the failing statement.
  If failure persists, store with `verified=False` and `low_confidence=True` (never drop silently).
- Every metric extraction and every chat answer must be able to trace back
  to which chunk(s)/page(s) it came from — build this into the prompt and
  the response schema from the start, not bolted on later.
- Re-verify free model IDs against `openrouter.ai/models` before relying on
  a specific ID long-term — they rotate.

---

## 9. Security & secrets

- No API keys, connection strings, or credentials in committed code, ever
  — `.env` only, and `.env` is gitignored. `.env.example` holds names only,
  no real values.
- CORS on the FastAPI backend restricted to the actual frontend domain(s),
  not `*`.
- Any user-supplied input (filenames, tags, chat questions) is validated/
  sanitized before it reaches a database query or a filesystem path.
- Frontend never holds a secret key — only `NEXT_PUBLIC_`-prefixed values
  that are genuinely safe to expose to a browser.

---

## 10. Testing

- Every ratio calculation (`Gross Margin`, `ROE`, etc.) gets a unit test
  with known inputs/outputs — this is pure arithmetic, it should never
  regress silently.
- Pre-ingestion upload validator gets tests covering text density (< 200 chars),
  unsupported form types, and valid `10-K`, `10-Q`, `20-F` filings.
- Every metric extraction path gets unit tests mocking the LLM: assert exactly
  one call per document on the happy path, assert hallucinated values are rejected
  by the grounding check, assert balance-sheet mismatches trigger one retry, and
  assert Python unit scaling is applied correctly.
- Every API route gets at least one happy-path test and one
  invalid-input test.
- Ingestion idempotency gets an explicit test: ingest the same file twice,
  assert no duplicate rows.
- Don't mark a phase/task complete in TRACKING.md without the relevant
  tests passing.

---

## 11. Git / PR workflow

- Small, focused commits. One logical change per commit, descriptive
  message (what changed and why, not just "update files").
- No force-push to a shared branch.
- No rewriting a migration that's already been applied to the Supabase
  instance — write a new migration instead.
- If a change touches an ADR or a "Decided" row in PROJECT.md's tech table,
  say so explicitly in the PR description.

---

## 12. Quick-reference: Do / Don't

| Do | Don't |
|---|---|
| Read PROJECT.md before starting any task | Assume you know the architecture from the file names alone |
| Flag invented specifics explicitly | Present a guessed value as a settled decision |
| Use `NUMERIC`/`Decimal` for money | Use `float` anywhere near a dollar amount |
| Compute ratios in Python | Ask an LLM to compute or persist a ratio |
| Route all LLM calls through `/llm` | Call OpenRouter directly from a route handler |
| Keep tables whole per chunk | Split a table mid-row when chunking |
| Add new env vars to `.env.example` | Commit a real credential or `.env` file |
| Write a new migration for schema changes | Hand-edit the Supabase schema outside version control |
| Validate text density & form type before ingestion | Send image-only PDFs or unsupported forms to Docling |
| Batch primary statements into 1 call with unscaled values | Call LLM per table or ask LLM to scale numbers |
| Verify numbers verbatim against source table text | Trust LLM extracted numbers without grounding check |
| Check accounting equations with single retry | Drop failing metrics silently |
| Ask/flag when a hard constraint (§1) is in tension with a task | Find a technically-compliant workaround that defeats the constraint's purpose |
