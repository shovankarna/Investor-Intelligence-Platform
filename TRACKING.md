# Investor Intelligence Platform — Implementation Tracker & Roadmap

> **Status:** Active Project Tracking Document  
> **Source Spec:** [`PROJECT.md`](file:///d:/Dev/Projects-AI/RAG-Project/RAG-Project-1/Investor-Intelligence-Platform/PROJECT.md)  
> **Last Updated:** 2026-09-21  

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
        EP_ING["/api/ingest (Docling Parser)"]
        EP_MET["/api/metrics (CRUD & Financial Math)"]
        EP_CHAT["/api/chat (Router + Hybrid Search + LLM)"]
        
        MOD_EMB["Local sentence-transformers\n(BAAI/bge-small-en-v1.5)"]
        MOD_RERANK["Local Cross-Encoder Reranker\n(BAAI/bge-reranker-base)"]
    end

    subgraph DB["Postgres + pgvector (Supabase Free Tier)"]
        TBL_DOCS["documents (content_hash)"]
        TBL_MET["financial_metrics (raw line items)"]
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
    EP_ING -->|Table Stream| OR_GATEWAY
    OR_GATEWAY -->|Structured JSON| TBL_MET
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
| **Text Embedding** | `BAAI/bge-small-en-v1.5` | In-Process `sentence-transformers` | Free, runs in memory (~130MB footprint) |
| **Cross-Encoder Reranker** | `BAAI/bge-reranker-base` | In-Process `sentence-transformers` | Free, runs in memory (~400MB footprint) |
| **Database & Vectors** | Supabase Postgres + `pgvector` | Managed Supabase Cloud | Free Tier (500MB storage, pgvector enabled) *(inferred — verify against Supabase's current published limits before relying on this)* |
| **File Storage** | Supabase Storage | Managed Supabase Cloud | Free Tier (1GB storage for uploaded PDFs) *(inferred — verify against Supabase's current published limits before relying on this)* |
| **LLM Provider** | OpenRouter Free Tier | External HTTP REST API | 20 req/min global limit; multi-model fallback |
| **Frontend Web App** | Next.js 14+ / React / TailwindCSS | Vercel Deployment | Free Tier (Hobby) |

---

## 3. Data Dictionary & Contract Specification

### 3.1 Postgres Database Schema

#### `documents`
- `id` (SERIAL PRIMARY KEY)
- `company` (TEXT NOT NULL)
- `fiscal_year` (INTEGER NOT NULL)
- `filename` (TEXT NOT NULL)
- `storage_path` (TEXT)
- `content_hash` (TEXT UNIQUE NOT NULL) — SHA256 hash for idempotent upsert
- `upload_date` (TIMESTAMPTZ DEFAULT NOW())

#### `financial_metrics`
- `id` (SERIAL PRIMARY KEY)
- `document_id` (INTEGER REFERENCES documents(id) ON DELETE CASCADE)
- `metric_name` (TEXT NOT NULL) — standard snake_case key
- `value` (NUMERIC NOT NULL)
- `unit` (TEXT NOT NULL) — e.g., `'USD_millions'`, `'USD_thousands'`, `'USD_units'`
- `currency` (TEXT NOT NULL DEFAULT `'USD'`)
- `source_page` (INTEGER NOT NULL)
- `source_chunk_id` (TEXT)
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
- [ ] **0.1 Repository & Workspace Structure**
  - [ ] Initialize backend directory (`/backend`) with Python virtual environment.
  - [ ] Initialize frontend directory (`/frontend`) with Next.js App Router. (inferred — not in PROJECT.md, needs confirmation)
  - [ ] Configure root-level `.gitignore`, `.env.example`, and development scripts.
- [ ] **0.2 Database & Supabase Configuration**
  - [ ] Create Supabase project in the chosen region. (touches PROJECT.md §11 Open Question: pick geographically close regions for Cloud Run and Supabase to minimize cross-service latency)
  - [ ] Enable `pgvector` extension in Postgres (`CREATE EXTENSION IF NOT EXISTS vector;`).
  - [ ] Execute SQL schema migrations for `documents`, `financial_metrics`, `chunks`, `chat_logs`.
  - [ ] Create GIN index on `tsv_content` for full-text search and HNSW index on `embedding`.
  - [ ] Set up Supabase Storage bucket for PDF documents with access policies.
- [ ] **0.3 OpenRouter Client & Resiliency Layer**
  - [ ] Implement OpenRouter API client supporting structured JSON output and function calling.
  - [ ] Implement fallback chain: `deepseek/deepseek-v4-flash:free` -> `moonshotai/kimi-k2.6:free` -> `nex-agi/nex-n2-pro:free` -> `openrouter/free`.
  - [ ] Implement exponential backoff retry handler for HTTP 429 and 5xx responses.

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
- [ ] **1.2 Layout-Aware Parsing with Docling**
  - [ ] Integrate Docling parser to extract document layout tree.
  - [ ] Preserve hierarchical section paths (e.g., `Part I > Item 1. Business`).
  - [ ] Extract page numbers per bounding block.
  - [ ] Distinguish narrative text elements (headings, paragraphs) from tabular elements.
- [ ] **1.3 Ingestion Stream Fork**
  - [ ] Route all structured tables to the Table Ingestion / Metric Extraction pipeline.
  - [ ] Route all narrative prose and headings to the Text Chunking & Embedding pipeline.

---

### Phase 2: Narrative Chunking, Embedding & pgvector Storage
- [ ] **2.1 Structure-Aware Chunking Strategy**
  - [ ] Implement Markdown/heading-aware chunker respecting section boundaries.
  - [ ] Enforce chunk token limits (target: 300–600 tokens with 10% overlap).
  - [ ] Format whole tables as Markdown/HTML strings, guaranteeing zero mid-row splits.
  - [ ] Tag every chunk with: `document_id`, `page_number`, `section_path`, `element_type`.
- [ ] **2.2 Local Embedding Generation**
  - [ ] Load `BAAI/bge-small-en-v1.5` in backend using `sentence-transformers`.
  - [ ] Implement batched embedding generation for all document chunks.
  - [ ] Normalize embeddings for cosine similarity.
- [ ] **2.3 Batch Insertion to Supabase**
  - [ ] Insert chunk records into `chunks` table with `tsv_content` and vector embeddings.
  - [ ] Validate vector dimensions (384-d).

---

### Phase 3: Structured Metric Extraction & Line-Item Persistence
- [ ] **3.1 Financial Metric Extraction Engine**
  - [ ] Filter Docling tables specifically containing Financial Statements (Income Statement, Balance Sheet, Cash Flows).
  - [ ] Formulate JSON schema for raw line items (13 target metrics) with unit and currency.
  - [ ] Call OpenRouter structured generation model to map table figures to standard metric keys.
  - [ ] Force LLM to cite `source_page` and `source_chunk_id` for each metric extracted.
- [ ] **3.2 Metric Validation & Storage**
  - [ ] Clean and normalize values (scaling thousands/millions to base numbers, verifying negative parentheses).
  - [ ] Upsert metrics into `financial_metrics` table with unique constraint on `(document_id, metric_name)`.
  - [ ] Provide rollback / error handling if extraction fails.
- [ ] **3.3 Financial Calculations Service**
  - [ ] Implement pure Python service calculating Margins, FCF, Debt-to-Equity, ROE, ROA.
  - [ ] Implement multi-year YoY growth rate calculation across available fiscal years for the same company.

---

### Phase 4: Frontend Dashboard & Financial Analytics UI
- [ ] **4.1 Core Design System & UI Shell (Next.js)**
  - [ ] Set up layout with dark mode, modern typography (Inter/Outfit), and sleek cards. (inferred — not in PROJECT.md, needs confirmation)
  - [ ] Build global navigation bar, company selector dropdown, and fiscal year filter.
  - [ ] Implement Document Upload modal with progress indicators.
- [ ] **4.2 Company Financial Overview Page**
  - [ ] KPI summary cards displaying core metrics and calculated ratios with YoY badges.
  - [ ] Income Statement, Balance Sheet, and Cash Flow interactive data tables.
  - [ ] Interactive charts (Revenue & Net Income trends, Profit Margin evolution, Cash Flow vs CapEx). (inferred — not in PROJECT.md, needs confirmation)
- [ ] **4.3 Multi-Company Comparison Dashboard**
  - [ ] Side-by-side metric comparison table for 2+ companies.
  - [ ] Comparative normalized bar charts and radar charts. (inferred — not in PROJECT.md, needs confirmation)
- [ ] **4.4 Metric Provenance Modal**
  - [ ] Click-through on any metric value to reveal source document, page number, and source table snippet.

---

### Phase 5: Retrieval-Augmented Generation & Chat Agent
- [ ] **5.1 Query Router**
  - [ ] Classify user query intent into:
    - `STRUCTURED`: Pure metric lookup or ratio computation -> routes to SQL query generator.
    - `NARRATIVE`: Qualitative, strategic, or risk factor questions -> routes to pgvector hybrid search.
    - `HYBRID`: "Why did revenue drop despite margin expansion?" -> runs parallel structured + narrative retrieval.
  - [ ] Detect single-company vs multi-company comparison queries.
- [ ] **5.2 Hybrid Search & Cross-Encoder Reranking**
  - [ ] Execute combined SQL query: `pgvector` Cosine Similarity + `tsvector` Keyword Full-Text Search.
  - [ ] Retrieve top-K candidate chunks (top-K = 20).
  - [ ] Rerank candidates using local `BAAI/bge-reranker-base` cross-encoder down to top-N (top-N = 5).
- [ ] **5.3 RAG Synthesis Prompt & Citation Injection**
  - [ ] Construct prompt with retrieved chunks formatted as `[Chunk {id}: Doc {doc}, Page {page}, Section {section}]`. (inferred — not in PROJECT.md, needs confirmation)
  - [ ] Enforce structured LLM output schema with answer text and `citations: [{chunk_id, page_number}]` array.
  - [ ] Deliver buffered (non-streaming) LLM response with citations payload to frontend chat interface for v1.
- [ ] **5.4 Interactive Citation UI**
  - [ ] Render clickable citation pills in chat messages.
  - [ ] Opening a citation displays the exact text excerpt, section breadcrumbs, and a link/preview of the PDF page.

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
  - [ ] End-to-end test: Upload PDF -> Ingestion -> Dashboard Display -> Conversational Query with Citation.

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
- [ ] **Security & Observability:**
  - [ ] Add CORS policies restricting API access to Vercel domain. (inferred — not in PROJECT.md, needs confirmation)
  - [ ] Log chat queries and retrieval performance in `chat_logs`.

---

## 6. How to Use & Update this Tracker

1. **Check off tasks (`[x]`)** as they are developed and verified.
2. **Review Open Questions** in [`PROJECT.md`](file:///d:/Dev/Projects-AI/RAG-Project/RAG-Project-1/Investor-Intelligence-Platform/PROJECT.md#11-open-questions--tbd) whenever infrastructure decisions arise.
3. **Log deviations or new ADRs** in this tracker and keep [`PROJECT.md`](file:///d:/Dev/Projects-AI/RAG-Project/RAG-Project-1/Investor-Intelligence-Platform/PROJECT.md) synchronized.
