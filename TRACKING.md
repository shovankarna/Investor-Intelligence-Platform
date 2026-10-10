# Investor Intelligence Platform — Implementation Tracker & Roadmap

> **Status:** Active Project Tracking Document  
> **Source Spec:** [`PROJECT.md`](file:///d:/Dev/Projects-AI/RAG-Project/RAG-Project-1/Investor-Intelligence-Platform/PROJECT.md)  
> **Last Updated:** 2026-10-08  

---

## Inferred Defaults — Needs Review

> _Changelog (2026-09-21): Items resolved in [`PROJECT.md`](file:///d:/Dev/Projects-AI/RAG-Project/RAG-Project-1/Investor-Intelligence-Platform/PROJECT.md#12-implementation-defaults-resolved-2026-09-19) §12 (DB index types, content hash algorithm, chunk parameters, vector normalization & validation, metric value cleaning, query router taxonomy, retrieval candidate pool & reranker cutoff, citation delivery schema, response buffering) were synced and removed from this list._

The following items are specific values, formats, architectures, or limits introduced during tracker authoring that do not appear in [`PROJECT.md`](file:///d:/Dev/Projects-AI/RAG-Project/RAG-Project-1/Investor-Intelligence-Platform/PROJECT.md). Each item is tagged inline in the tracker below and requires explicit confirmation before implementation:

1. **Supabase Free-Tier Storage Limits (§2 Technology Matrix):** 500MB DB / 1GB file storage limits quoted — verify against Supabase's current published limits before relying on this.
2. **Next.js App Router (Task 0.1):** Assumes Next.js App Router paradigm; `PROJECT.md` specifies Next.js (React) without mandating router architecture.
3. **UI Typography & Dark Theme Tokens (Task 4.1):** Specifies Inter/Outfit typography and dark mode shell; `PROJECT.md` specifies a Next.js frontend without font or aesthetic constraints.
4. **Overview Chart Selection (Task 4.2):** Selects specific visual charts (Revenue/Net Income trends, Profit Margin evolution, Cash Flow vs CapEx); `PROJECT.md` requires general charts and tables.
5. **Comparative Visualization Types (Task 4.3):** Proposes radar charts and normalized bar charts; `PROJECT.md` specifies multi-company comparison without naming radar charts.
6. **RAG Prompt Chunk Template (Task 5.3):** Defines `[Chunk {id}: Doc {doc}, Page {page}, Section {section}]` format; `PROJECT.md` specifies chunk metadata persistence without rigid prompt syntax.
7. **Evaluation Metric Granularity (Task 6.2):** Adds automated retrieval precision/recall and router accuracy benchmarks; `PROJECT.md` §12 specifies a 15–20 QA pair ground-truth dataset.
8. **Report Export Capabilities (Task 7.3):** Adds PDF/Excel summary export to post-v1 backlog; not listed in `PROJECT.md` §10 roadmap.
9. **Dockerfile Model Weight Caching (Section 5 Deployment):** Proposes baking Hugging Face model weights into the container image; `PROJECT.md` specifies in-process models without container build specifics.
10. **Cloud Run Memory Bounds (Section 5 Deployment):** Proposes 1.5GB to 2GB memory allocation; `PROJECT.md` notes models fit within free-tier GiB-seconds without quoting an exact container RAM size.
11. **CORS Origin Whitelisting (Section 5 Deployment):** Proposes explicit Vercel domain CORS restrictions; `PROJECT.md` does not specify CORS policies.

---

## 1. Executive Summary & Core Architectural Principles

The **Investor Intelligence Platform** is a dual-path RAG and financial analytics engine designed to ingest corporate financial reports (e.g., 10-K, Annual Reports in PDF format), extract structured metrics and narrative context with strict provenance metadata, and provide an interactive dashboard and citation-backed conversational assistant.

### 🛡️ Non-Negotiable Rules & ADR Reference
- **ADR-1 (Numbers via Structured Query Only):** Quantitative metrics are extracted at ingestion, saved to Postgres, and read directly. Vector embeddings are never used for arithmetic or quantitative lookups.
- **ADR-2 (Provenance-First Citations):** Every record in `financial_metrics` and `chunks` must carry `source_file`, `page_number`, and `section_path`.
- **ADR-3 (User-Supplied Ingestion):** Ingestion is manual upload + user tagging (`company`, `fiscal_year`) at v1.
- **ADR-4 (Pure Arithmetic in Code):** Financial ratios (Margins, FCF, Debt-to-Equity, ROE, ROA, YoY Growth) are calculated deterministically in application code, never generated or persisted by LLMs.
- **ADR-5 (OpenRouter Unified Stack):** All LLM generation routes through OpenRouter free-tier models with dynamic multi-tier fallback chains.
- **ADR-6 (Unified Database):** Both structured records and vector embeddings live inside a single Supabase Postgres instance utilizing the `pgvector` extension and `tsvector` full-text search.
- **ADR-7 (Pre-Ingestion Upload Validation):** Prior to ingestion, uploaded PDFs must pass text-density validation (>= 200 chars on first 3 pages) and form-type classification (`10-K`, `10-Q`, `20-F`). Non-text/scanned PDFs and unsupported forms are rejected with HTTP 422. Form type determines accounting alias mapping (US GAAP vs IFRS).
- **ADR-8 (LLM-First Metric Extraction with Deterministic Verification):** Candidate tables are filtered down to primary financial statements (Operations, Balance Sheet, Cash Flows); all footnote/non-primary tables are pruned. All selected statements are batched into ONE LLM call with unscaled printed values. Returned numbers must pass verbatim grounding checks against source table text. Accounting equations (`Assets == Liabilities + Equity`, `Gross Profit == Revenue - COGS`) are validated in Python with single-statement retry. Unit scaling is applied deterministically in Python post-verification.

---

## 2. System Architecture & Tech Stack

```mermaid
flowchart TD
    subgraph Client["Frontend (Next.js on Vercel)"]
        UI_UP["Upload & Tagging Modal"]
        UI_DASH["Financial Dashboard (Charts & Ratios)"]
        UI_CHAT["Chat Agent UI with Citations"]
        UI_VIEW["PDF Page & Excerpt Viewer"]
    end

    subgraph Server["Backend API (FastAPI on Google Cloud Run)"]
        EP_ING["/api/documents/upload (Upload Validator + Docling)"]
        EP_MET["/api/metrics (CRUD & Financial Math)"]
        EP_CHAT["/api/chat (Router + Hybrid Search + LLM)"]
        
        MOD_EMB["Local sentence-transformers\n(BAAI/bge-small-en-v1.5)"]
        MOD_RERANK["Local Cross-Encoder Reranker\n(BAAI/bge-reranker-base)"]
    end

    subgraph DB["Postgres + pgvector (Supabase Free Tier)"]
        TBL_DOCS["documents (content_hash, form_type, fiscal_year_end)"]
        TBL_MET["financial_metrics (verified, low_confidence)"]
        TBL_CHUNKS["chunks (embedding vector + tsvector)"]
        TBL_LOGS["chat_logs"]
        SUPA_STORE["Supabase Storage (Original PDFs)"]
    end

    subgraph External["External LLM Provider"]
        OR_GATEWAY["OpenRouter Gateway"]
        M_PRIMARY["deepseek/deepseek-v4-flash:free"]
        M_FALLBACK1["moonshotai/kimi-k2.6:free"]
        M_FALLBACK2["nex-agi/nex-n2-pro:free"]
        M_FALLBACK3["openrouter/free"]
    end

    UI_UP --> EP_ING
    EP_ING --> SUPA_STORE
    EP_ING --> TBL_DOCS
    EP_ING -->|Primary Statement Stream (1 Batched Call)| OR_GATEWAY
    OR_GATEWAY -->|Printed Unscaled JSON| TBL_MET
    EP_ING -->|Narrative Stream| MOD_EMB
    MOD_EMB --> TBL_CHUNKS

    UI_DASH --> EP_MET
    EP_MET --> TBL_MET

    UI_CHAT --> EP_CHAT
    EP_CHAT --> TBL_MET
    EP_CHAT --> TBL_CHUNKS
    TBL_CHUNKS --> MOD_RERANK
    MOD_RERANK --> OR_GATEWAY
    OR_GATEWAY --> EP_CHAT
    EP_CHAT --> UI_CHAT
    UI_CHAT -.->|View Citation| UI_VIEW
    UI_VIEW --> SUPA_STORE
```

### Technology Matrix
| Layer | Chosen Tool | Execution Context | Pricing / Constraints |
|---|---|---|---|
| **Backend API** | FastAPI (Python 3.11+) | Google Cloud Run Container | Free Tier (180k vCPU-s, 360k GiB-s/mo) |
| **PDF Parser** | Docling | In-Process Backend Worker | Open-source, layout-aware, preserves tables/headings |
| **Pre-Ingestion Validator** | `upload_validator.py` | In-Process Backend Service | Rejects scanned PDFs (<200 chars) & unsupported forms (HTTP 422) |
| **Text Embedding** | `BAAI/bge-small-en-v1.5` | In-Process `sentence-transformers` | Free, runs in memory (~130MB footprint) |
| **Cross-Encoder Reranker** | `BAAI/bge-reranker-base` | In-Process `sentence-transformers` | Free, runs in memory (~400MB footprint) |
| **Database & Vectors** | Supabase Postgres + `pgvector` | Managed Supabase Cloud | Free Tier (500MB storage, pgvector enabled, Supavisor pooler) |
| **File Storage** | Supabase Storage | Managed Supabase Cloud | Free Tier (1GB storage for uploaded PDFs, `filings` bucket) |
| **LLM Provider** | OpenRouter Free Tier | External HTTP REST API | 20 req/min global limit; multi-model fallback |
| **Observability & Tracing** | Langfuse (Cloud Free Tier) | External Telemetry API | Free Tier (50k traces/mo); tracks tokens, latencies, fallbacks, and RAG traces via `@observe` |
| **Metric Extraction** | LLM + Deterministic Verification | OpenRouter + Python (`Decimal`) | 1 batched call, verbatim grounding, accounting checks retry, unit scaling |
| **Frontend Web App** | Next.js 14+ / React / TailwindCSS | Vercel Deployment | Free Tier (Hobby) |

---

## 3. Data Dictionary & Contract Specification

### 3.1 Postgres Database Schema

#### `documents`
- `id` (SERIAL PRIMARY KEY)
- `company` (TEXT NOT NULL)
- `fiscal_year` (INTEGER NOT NULL)
- `form_type` (VARCHAR(20) NOT NULL DEFAULT '10-K') — `'10-K'`, `'10-Q'`, `'20-F'`
- `fiscal_year_end` (VARCHAR(100)) — extracted FYE date string (e.g. `'September 30, 2023'`)
- `filename` (TEXT NOT NULL)
- `storage_path` (TEXT)
- `content_hash` (TEXT UNIQUE NOT NULL) — SHA256 hash for idempotent upsert
- `upload_date` (TIMESTAMPTZ DEFAULT NOW())

#### `financial_metrics`
- `id` (SERIAL PRIMARY KEY)
- `document_id` (INTEGER REFERENCES documents(id) ON DELETE CASCADE)
- `metric_name` (TEXT NOT NULL) — standard snake_case key
- `value` (NUMERIC NOT NULL) — base units in Decimal
- `unit` (TEXT NOT NULL) — e.g., `'USD_units'`, `'USD_millions'`, `'USD_thousands'`
- `currency` (TEXT NOT NULL DEFAULT `'USD'`)
- `source_page` (INTEGER NOT NULL)
- `source_chunk_id` (TEXT)
- `verified` (BOOLEAN NOT NULL DEFAULT TRUE) — verbatim grounding check result
- `low_confidence` (BOOLEAN NOT NULL DEFAULT FALSE) — flagged if accounting checks failed after retry
- *Constraint:* `UNIQUE (document_id, metric_name)`

#### `chunks`
- `id` (TEXT PRIMARY KEY) — e.g. `{doc_id}_p{page}_c{seq}`
- `document_id` (INTEGER REFERENCES documents(id) ON DELETE CASCADE)
- `page_number` (INTEGER NOT NULL)
- `section_path` (TEXT NOT NULL) — e.g., `'Item 7. MD&A > Results of Operations'`
- `element_type` (TEXT NOT NULL) — `'prose'` or `'table'`
- `content` (TEXT NOT NULL)
- `tsv_content` (TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED)
- `embedding` (VECTOR(384)) — generated by `bge-small-en-v1.5`

#### `chat_logs`
- `id` (SERIAL PRIMARY KEY)
- `question` (TEXT NOT NULL)
- `answer` (TEXT NOT NULL)
- `query_type` (TEXT) — `'structured'`, `'narrative'`, `'hybrid'`
- `retrieved_chunk_ids` (TEXT[])
- `created_at` (TIMESTAMPTZ DEFAULT NOW())

---

### 3.2 Standard Financial Metrics & Calculated Ratios

#### Extracted Raw Line Items (13 Target Metrics — LLM Target Schema):
| Statement | Metric Key (`metric_name`) | Display Name |
|---|---|---|
| **Income Statement** | `total_revenue` | Total Revenue |
| | `cost_of_revenue` | Cost of Revenue |
| | `gross_profit` | Gross Profit |
| | `operating_expenses` | Operating Expenses |
| | `operating_income` | Operating Income |
| | `net_income` | Net Income |
| | `diluted_eps` | Diluted Earnings Per Share |
| **Balance Sheet** | `total_assets` | Total Assets |
| | `total_liabilities` | Total Liabilities |
| | `stockholders_equity` | Total Stockholders' Equity |
| | `cash_and_equivalents` | Cash & Cash Equivalents |
| **Cash Flow** | `operating_cash_flow` | Operating Cash Flow |
| | `capital_expenditures` | Capital Expenditures (CapEx) |

#### Deterministically Computed Ratios (Python / Code layer):
- **Gross Margin (%)** = `(gross_profit / total_revenue) * 100`
- **Operating Margin (%)** = `(operating_income / total_revenue) * 100`
- **Net Margin (%)** = `(net_income / total_revenue) * 100`
- **Free Cash Flow** = `operating_cash_flow - capital_expenditures`
- **Debt-to-Equity** = `total_liabilities / stockholders_equity`
- **Return on Equity (ROE %)** = `(net_income / stockholders_equity) * 100`
- **Return on Assets (ROA %)** = `(net_income / total_assets) * 100`
- **YoY Growth (%)** = `((value_year_t - value_year_t_minus_1) / |value_year_t_minus_1|) * 100`

---

## 4. Master Implementation Roadmap & Step-by-Step Tracker

### Phase 0: Project Foundations & Infrastructure Setup
- [x] **0.1 Repository & Workspace Structure**
  - [x] Initialize backend directory (`/backend`) with Python virtual environment.
  - [ ] Initialize frontend directory (`/frontend`) with Next.js App Router. (inferred — not in PROJECT.md, needs confirmation)
  - [x] Configure root-level `.gitignore`, `.env.example`, and development scripts (`pyproject.toml`, test suites).
- [x] **0.2 Database & Supabase Configuration**
  - [x] Create Supabase project in the chosen region. (touches PROJECT.md §11 Open Question: pick geographically close regions for Cloud Run and Supabase to minimize cross-service latency)
  - [x] Enable `pgvector` extension in Postgres (`CREATE EXTENSION IF NOT EXISTS vector;`).
  - [x] Execute SQL schema migrations for `documents`, `financial_metrics`, `chunks`, `chat_logs` (Alembic versions 001, 002, 003).
  - [x] Create GIN index on `tsv_content` for full-text search and HNSW index on `embedding`.
  - [ ] Set up Supabase Storage bucket for PDF documents with access policies.
- [x] **0.3 OpenRouter Client & Resiliency Layer**
  - [x] Implement OpenRouter API client supporting structured JSON output and function calling (`app/llm/client.py`).
  - [x] Implement fallback chain: `nvidia/nemotron-3.5-lightning:free` -> `google/gemma-4-31b-it:free` -> `nvidia/nemotron-3-super-120b-a12b:free` -> `openrouter/free`.
  - [x] Implement exponential backoff retry handler for HTTP 429 and 5xx responses.
  - [x] Integrate Langfuse `@observe` telemetry to monitor token usage, latencies, and model failover events.

---

### Phase 1: PDF Ingestion Engine & Layout-Aware Docling Parser
- [x] **1.1 Ingestion API Endpoint & Pre-Ingestion Validator (`POST /api/documents/upload`)**
  - [x] Pre-ingestion validation (`validate_upload` in `app/services/upload_validator.py`):
    - [x] Text layer validation (rejects scanned/image-only PDFs < 200 chars with HTTP 422).
    - [x] Form type classification (supports `10-K`, `10-Q`, `20-F`; rejects unsupported/unknown with HTTP 422).
    - [x] Fiscal year end date metadata extraction.
  - [x] Accept `file` (PDF), `company` (string), `fiscal_year` (int).
  - [x] Calculate SHA-256 `content_hash` of uploaded PDF.
  - [x] Check for existing document by `content_hash` (Idempotency handler: upsert or skip duplicate).
  - [x] Insert record into `documents` table with `form_type` and `fiscal_year_end`.
  - [x] Pick accounting alias map based on `form_type` (US GAAP for 10-K/10-Q, IFRS for 20-F).
- [x] **1.2 Layout-Aware Parsing with Docling**
  - [x] Integrate Docling parser to extract document layout tree (`app/services/parser_service.py`).
  - [x] Preserve hierarchical section paths (e.g., `Part I > Item 1. Business`).
  - [x] Extract page numbers per bounding block.
  - [x] Distinguish narrative text elements (headings, paragraphs) from tabular elements.
- [x] **1.3 Ingestion Stream Fork**
  - [x] Route all structured tables to the Table Ingestion / Metric Extraction pipeline.
  - [x] Route all narrative prose and headings to the Text Chunking & Embedding pipeline.

---

### Phase 2: Narrative Chunking, Embedding & pgvector Storage
- [x] **2.1 Structure-Aware Chunking Strategy**
  - [x] Implement Markdown/heading-aware chunker respecting section boundaries (`app/rag/chunker.py`).
  - [x] Enforce chunk token limits (target: 300–600 tokens with 10% overlap).
  - [x] Format whole tables as Markdown/HTML strings, guaranteeing zero mid-row splits.
  - [x] Tag every chunk with: `document_id`, `page_number`, `section_path`, `element_type`.
- [x] **2.2 Local Embedding Generation**
  - [x] Load `BAAI/bge-small-en-v1.5` in backend using `sentence-transformers` (`app/rag/embedder.py`).
  - [x] Implement batched embedding generation for all document chunks.
  - [x] Normalize embeddings for cosine similarity.
- [x] **2.3 Batch Insertion to Supabase**
  - [x] Insert chunk records into `chunks` table with `tsv_content` and vector embeddings (`app/services/document_service.py`).
  - [x] Validate vector dimensions (384-d).

---

### Phase 3: Structured Metric Extraction & Line-Item Persistence
- [x] **3.1 Financial Metric Extraction Engine (LLM-First with Deterministic Verification)**
  - [x] Primary statement filter (Consolidated Operations/Income, Balance Sheets, Cash Flows) dropping all footnote/non-primary tables.
  - [x] Batched OpenRouter extraction sending all primary statements in ONE single call with unscaled printed values.
  - [x] Verbatim grounding check per metric against source table text.
  - [x] Deterministic Python accounting checks (Balance Sheet: Assets == Liabilities + Equity; Operations: Gross Profit == Revenue - COGS).
  - [x] Single statement retry on accounting check failure with fallback to low_confidence flag (no silent drops).
- [x] **3.2 Metric Validation & Storage**
  - [x] Apply mathematical unit scaling in Python after verification (millions -> base units; EPS untouched).
  - [x] Store `verified` and `low_confidence` flags on `financial_metrics` table with Alembic migration.
  - [x] Upsert metrics into `financial_metrics` table with unique constraint on `(document_id, metric_name)`.
- [x] **3.3 Financial Calculations Service**
  - [x] Implement pure Python service calculating Margins, FCF, Debt-to-Equity, ROE, ROA.
  - [x] Implement multi-year YoY growth rate calculation across available fiscal years for the same company.

---

### Phase 4: Frontend Dashboard & Financial Analytics UI
- [x] **4.1 Core Design System & UI Shell (Next.js)**
  - [x] Set up layout with dark mode, modern typography, and sleek glassmorphism cards.
  - [x] Build global navigation bar, company selector dropdown, and fiscal year filter.
  - [x] Implement Document Upload modal with pre-ingestion validation rules and progress indicators.
- [x] **4.2 Company Financial Overview Page**
  - [x] KPI summary cards displaying core metrics and calculated ratios with YoY badges.
  - [x] Income Statement, Balance Sheet, and Cash Flow interactive data tables.
  - [x] Interactive zero-dependency SVG charts (Revenue & Net Income trends, Profit Margin evolution, Cash Flow vs CapEx).
- [x] **4.3 Multi-Company Comparison Dashboard**
  - [x] Side-by-side metric comparison table for 2+ companies.
  - [x] Comparative normalized scale benchmark bar charts.
- [x] **4.4 Metric Provenance Modal**
  - [x] Click-through on any metric value to reveal source document, page number, verbatim verification status, and audit lineage.

---

### Phase 5: Retrieval-Augmented Generation & Chat Agent
- [x] **5.1 Query Router (Backend)**
  - [x] Classify user query intent into:
    - `STRUCTURED`: Pure metric lookup or ratio computation -> routes to SQL query generator.
    - `NARRATIVE`: Qualitative, strategic, or risk factor questions -> routes to pgvector hybrid search.
    - `HYBRID`: "Why did revenue drop despite margin expansion?" -> runs parallel structured + narrative retrieval.
  - [x] Detect single-company vs multi-company comparison queries.
- [x] **5.2 Hybrid Search & Cross-Encoder Reranking (Backend)**
  - [x] Execute combined SQL query: `pgvector` Cosine Similarity + `tsvector` Keyword Full-Text Search.
  - [x] Retrieve top-K candidate chunks (top-K = 20).
  - [x] Rerank candidates using local `BAAI/bge-reranker-base` cross-encoder down to top-N (top-N = 5).
- [x] **5.3 RAG Synthesis Prompt & Citation Injection (Backend)**
  - [x] Construct prompt with retrieved chunks formatted as `[Chunk {id}: Doc {doc}, Page {page}, Section {section}]`.
  - [x] Enforce structured LLM output schema with answer text and `citations: [{chunk_id, page_number}]` array.
  - [x] Deliver buffered (non-streaming) LLM response with citations payload to frontend chat interface for v1.
- [x] **5.4 Interactive Citation UI (Frontend)**
  - [x] Render clickable citation pills in chat messages with query routing intent badge (`[STRUCTURED]`, `[NARRATIVE]`, `[HYBRID]`).
  - [x] Opening a citation displays the exact text excerpt, section breadcrumbs, element classification, and page number in an audit modal.

---

### Phase 6: Groundedness Validation, Evaluation & Quality Assurance
- [ ] **6.1 Post-Generation Groundedness Checker**
  - [ ] Implement verification check to ensure all numbers/claims in generated answer exist in retrieved context.
  - [ ] Flag or refuse hallucinations where confidence or grounding is insufficient.
- [ ] **6.2 Automated Evaluation Dataset**
  - [ ] Construct benchmark test suite (15–20 curated question/answer pairs per company report).
  - [ ] Test metric extraction accuracy against ground-truth SEC 10-K tables.
  - [ ] Test retrieval precision/recall and router classification accuracy. (inferred — not in PROJECT.md, needs confirmation)
- [ ] **6.3 Integration & End-to-End Testing**
  - [x] Backend API route integration and idempotency test suite (`test_api_routes.py` with 15 passing tests).
  - [ ] Full end-to-end test: Upload PDF -> Ingestion -> Dashboard Display -> Conversational Query with Citation (requires frontend).

---

### Phase 7 & 8: Backlog & Enhancements (Post-v1)
- [ ] **7.1 SEC EDGAR Automated Fetcher**
  - [ ] Look up ticker / CIK and download official 10-K/10-Q filing automatically.
- [ ] **7.2 Multi-Format Parser Support**
  - [ ] Support HTML filings (iXBRL) and scanned OCR PDFs.
- [ ] **7.3 Export & Report Generation**
  - [ ] Export comparative financial summary as PDF or Excel sheet. (inferred — not in PROJECT.md, needs confirmation)

---

## 5. Deployment & Production Operations

- [ ] **Backend (FastAPI on Google Cloud Run):**
  - [ ] Create multi-stage `Dockerfile` caching Hugging Face model weights (`bge-small-en-v1.5`, `bge-reranker-base`) inside the image to minimize cold-start latency. (inferred — not in PROJECT.md, needs confirmation)
  - [ ] Configure Cloud Run CPU allocation, memory (1.5GB to 2GB), and concurrency. (inferred — not in PROJECT.md, needs confirmation)
  - [ ] Test cold-start times and decide on `min-instances: 0` (scale-to-zero free tier) vs `min-instances: 1`. (touches PROJECT.md §11 Open Question: min-instances 1 to avoid cold-start delay vs staying fully within always-free tier)
- [ ] **Frontend (Next.js on Vercel):**
  - [ ] Configure environment variables (`NEXT_PUBLIC_API_URL`, Supabase public keys).
  - [ ] Set up automated GitHub CI/CD deployments.
- [x] **Security & Observability:**
  - [x] Add CORS policies with flexible JSON / comma-separated string parsing restricting API access.
  - [x] Integrate Langfuse Cloud telemetry (`@observe`) for token, latency, and full RAG trace observability.
  - [x] Log chat queries and retrieval performance in `chat_logs`.

---

## 6. How to Use & Update this Tracker

1. **Check off tasks (`[x]`)** as they are developed and verified.
2. **Review Open Questions** in [`PROJECT.md`](file:///d:/Dev/Projects-AI/RAG-Project/RAG-Project-1/Investor-Intelligence-Platform/PROJECT.md#11-open-questions--tbd) whenever infrastructure decisions arise.
3. **Log deviations or new ADRs** in this tracker and keep [`PROJECT.md`](file:///d:/Dev/Projects-AI/RAG-Project/RAG-Project-1/Investor-Intelligence-Platform/PROJECT.md) synchronized.
