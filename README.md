# AI SDR — Autonomous Sales Development Rep

An open-source-first AI Sales Development Rep. It finds leads, researches them, scores fit, writes personalized outreach, handles replies, and books meetings, all through an orchestrated multi-agent workflow.

This repository is a production-style project covering ingestion, RAG, agentic orchestration, evaluation, observability, and cloud deployment.

## Product Vision

Businesses define their ideal customer. The system then:

1. Ingests and enriches matching leads.
2. Scores each lead against the Ideal Customer Profile (ICP).
3. Researches each lead for personalization context.
4. Writes a tailored first message and follow-up sequence.
5. Handles replies (interested, objection, not now, book a meeting).
6. Tracks pipeline, quality, and observability metrics.

## Architecture (Target)

See [docs/architecture.md](docs/architecture.md) for full diagrams (target system, current build, and data flow).

Event-driven, multi-agent system with async workers:

- Ingestion workers: scrape and enrich leads to JSON.
- Redis queue + workers: process leads asynchronously.
- Lead scoring: rule-based plus LLM ICP fit.
- Research agent: builds a context profile (RAG over collected data).
- Orchestration (LangGraph): research -> write -> review -> send -> wait -> handle reply.
- Reply agent: classifies intent and responds.
- Scheduling agent: books meetings.
- Evaluation + observability: scores message quality and traces every step.

## Tech Stack (Open-Source-First)

- Language: Python
- API: FastAPI
- Orchestration / agents: LangGraph
- LLM: open-source models (Llama / Qwen) via Groq free API
- Vector DB: Pinecone (hosted embeddings)
- SQL DB: PostgreSQL
- Document DB: MongoDB Community
- Queue / workers: Redis + RQ
- Scraping: Playwright + BeautifulSoup
- Evaluation: RAGAS
- Observability: Langfuse or Phoenix
- Containerization: Docker + Docker Compose

Note: Pinecone and Groq are hosted services on free tiers; the models served are open source and everything we ship is portable.

## Roadmap

- [x] Lead ingestion + enrichment + ICP scoring.
- [x] Databases — PostgreSQL (leads, campaigns) + MongoDB (raw, logs).
- [ ] Pinecone vector memory + research agent (RAG, Groq).
- [ ] LangGraph outreach workflow (research -> write -> review -> send).
- [ ] Reply handling + scheduling agent + Redis async workers.
- [ ] RAGAS message-quality evals + Langfuse/Phoenix observability.
- [ ] Dockerize, deploy, and dashboard.

## Ingestion &amp; ICP Scoring

A runnable, dependency-free ingestion pipeline that turns raw leads into enriched, scored leads.

It derives:

- company domain
- seniority (from title)
- region (from location)
- ICP fit score with explanations

### Project Structure

```text
ai_sdr_agent/
  assets/
  data/
    raw/
    processed/
  reports/
  src/ai_sdr/
    config.py
    pipeline.py
    reporting.py
    sample_leads.py
    schemas.py
    storage.py
    ingestion/
      enrich.py
      sources.py
  .env.example
  README.md
  requirements.txt
```

### Run With Sample Data

```bash
cd ai_sdr_agent
PYTHONPATH=src python3 -m ai_sdr.pipeline --source sample
```

This creates:

- `data/raw/leads_raw.jsonl`
- `data/processed/leads.jsonl`
- `reports/ingestion_report.md`

### Run With Your Own File

```bash
PYTHONPATH=src python3 -m ai_sdr.pipeline --source file --input leads.csv
```

The file can be JSON or CSV with these columns:

`full_name, title, company, location, email, linkedin_url, company_website, industry, source`

## Database Persistence

This adds **polyglot persistence** — the right database for each kind of data:

- **PostgreSQL** stores structured, queryable records (`leads`, plus a `campaigns`
  scaffold). The `leads` table mirrors the `Lead` dataclass; `icp_reasons` is a
  `JSONB` column. Writes are **upserts** (`ON CONFLICT (lead_id) DO UPDATE`), so
  re-running the pipeline never creates duplicates.
- **MongoDB** stores loosely-shaped and append-only data: `raw_leads` (the lead
  exactly as ingested, upserted on a deterministic `_id`) and `run_logs` (one
  document per pipeline run).

### Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env   # then fill in MONGODB_URI / POSTGRES_URL
createdb ai_sdr        # one-time, local PostgreSQL
```

Configure `.env`:

- `POSTGRES_URL` — e.g. `postgresql://localhost:5432/ai_sdr`
- `MONGODB_URI` — local (`mongodb://localhost:27017/ai_sdr`) or Atlas
  (`mongodb+srv://<user>:<password>@<cluster>/ai_sdr?...`)

### Run With Persistence

```bash
PYTHONPATH=src .venv/bin/python -m ai_sdr.pipeline --source sample --persist
```

Without `--persist`, the pipeline behaves as the ingestion-only path (JSONL +
report only). With `--persist`, it additionally upserts leads into PostgreSQL and
stores raw leads + a run log in MongoDB. The database drivers are imported lazily,
so a non-persisting run requires no database at all.

### Code Layout

```text
src/ai_sdr/db/
  postgres.py   # connect, init_schema, upsert_leads, count_leads
  mongo.py      # connect, get_db, ping, store_raw_leads, log_run
```

## Pinecone Lead Memory

This is the first step toward the **research agent / RAG** milestone.

RAG has two halves:

1. **Indexing** — convert useful lead data into searchable memory.
2. **Retrieval + generation** — fetch relevant memory and ask the LLM to create a
   research profile.

This milestone is being built step by step. The project now supports indexing
lead memory and retrieving relevant records from Pinecone.

### Pinecone Setup

Create a Pinecone index that uses integrated embeddings. Configure its field map
so Pinecone embeds the text field named by `PINECONE_TEXT_FIELD`.

Configure `.env`:

- `PINECONE_API_KEY` — your Pinecone API key.
- `PINECONE_INDEX` — the index name, defaults to `ai-sdr-leads`.
- `PINECONE_NAMESPACE` — namespace for lead records, defaults to `leads`.
- `PINECONE_TEXT_FIELD` — text field Pinecone embeds, defaults to `text`.
- `GROQ_API_KEY` — required for Groq-powered research, writing, and review.
- `GROQ_MODEL` — defaults to `llama-3.3-70b-versatile`.

### Index Sample Leads

```bash
PYTHONPATH=src .venv/bin/python -m ai_sdr.pipeline --source sample --index-memory
```

Normal ingestion still works without Pinecone. The Pinecone SDK is imported lazily,
only when `--index-memory` is used.

### Search Lead Memory

Retrieval is the second half of RAG. It asks Pinecone: "which stored lead records
are closest to this question?"

```bash
PYTHONPATH=src .venv/bin/python -m ai_sdr.memory.search "AI founder in London" --top-k 3
```

To inspect the full stored context that will later be passed to the research
agent:

```bash
PYTHONPATH=src .venv/bin/python -m ai_sdr.memory.search "AI founder in London" --top-k 1 --show-text
```

Use metadata filters when a condition must be exact. In this example, Pinecone
searches semantically for "AI founder" but only inside leads whose normalized
region is `germany`:

```bash
PYTHONPATH=src .venv/bin/python -m ai_sdr.memory.search "AI founder" --region germany --top-k 1 --show-text
```

Available filters: `--region`, `--industry`, `--seniority`, and
`--min-icp-score`.

### Generate A Research Profile

The research profile is the first agent-facing artifact. It takes the best
retrieved lead-memory match and asks Groq to produce structured research context
for outreach writing.

```bash
PYTHONPATH=src .venv/bin/python -m ai_sdr.research.profile "AI founder" --region germany --save
```

This writes a Markdown profile under `reports/research_profiles/` when `--save`
is used. The profile includes a lead summary, ICP fit rationale, personalization
angles, possible pain points, an outreach hook, missing research, and source
context.

## Outreach Orchestration

This is the first step toward the **LangGraph outreach workflow** milestone. It
uses Groq for the writing and review decisions while keeping orchestration in
plain Python for now.

The workflow runs:

1. **Research** — retrieve lead memory and ask Groq to build a `ResearchProfile`.
2. **Write** — ask Groq to generate a first-touch `OutreachMessageDraft`.
3. **Review** — ask Groq to score, approve, or request revisions.

```bash
PYTHONPATH=src .venv/bin/python -m ai_sdr.outreach.workflow "AI founder" --region germany --save
```

This writes a Markdown run artifact under `reports/outreach_runs/` when `--save`
is used. The artifact contains the research profile, message draft, review
checks, and reviewer feedback.

## Next Steps

- Replace rule-based ICP scoring with an LLM scoring agent.
- Wrap the Groq-powered `research -> write -> review` contracts in LangGraph.
