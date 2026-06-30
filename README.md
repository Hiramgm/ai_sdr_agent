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
- [x] Pinecone vector memory + research agent (RAG, Groq).
- [x] LangGraph outreach workflow (research -> write -> review).
- [x] Reply classification agent.
- [x] Scheduling agent (meeting proposals from interested replies).
- [x] FastAPI demo API + web UI console.
- [x] Redis + RQ async workers (background outreach jobs).
- [x] Outreach quality evals + local observability events.
- [ ] RAGAS + Langfuse/Phoenix adapters.
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
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m ai_sdr.pipeline --source sample
```

This creates:

- `data/raw/leads_raw.jsonl`
- `data/processed/leads.jsonl`
- `reports/ingestion_report.md`

### Run With Your Own File

```bash
python -m ai_sdr.pipeline --source file --input leads.csv
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
source .venv/bin/activate
python -m pip install -e .
cp .env.example .env   # then fill in MONGODB_URI / POSTGRES_URL
createdb ai_sdr        # one-time, local PostgreSQL
```

Configure `.env`:

- `POSTGRES_URL` — e.g. `postgresql://localhost:5432/ai_sdr`
- `MONGODB_URI` — local (`mongodb://localhost:27017/ai_sdr`) or Atlas
  (`mongodb+srv://<user>:<password>@<cluster>/ai_sdr?...`)

### Run With Persistence

```bash
python -m ai_sdr.pipeline --source sample --persist
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
python -m ai_sdr.pipeline --source sample --index-memory
```

Normal ingestion still works without Pinecone. The Pinecone SDK is imported lazily,
only when `--index-memory` is used.

### Search Lead Memory

Retrieval is the second half of RAG. It asks Pinecone: "which stored lead records
are closest to this question?"

```bash
python -m ai_sdr.memory.search "AI founder in London" --top-k 3
```

To inspect the full stored context that will later be passed to the research
agent:

```bash
python -m ai_sdr.memory.search "AI founder in London" --top-k 1 --show-text
```

Use metadata filters when a condition must be exact. In this example, Pinecone
searches semantically for "AI founder" but only inside leads whose normalized
region is `germany`:

```bash
python -m ai_sdr.memory.search "AI founder" --region germany --top-k 1 --show-text
```

Available filters: `--region`, `--industry`, `--seniority`, and
`--min-icp-score`.

### Generate A Research Profile

The research profile is the first agent-facing artifact. It takes the best
retrieved lead-memory match and asks Groq to produce structured research context
for outreach writing.

```bash
python -m ai_sdr.research.profile "AI founder" --region germany --save
```

This writes a Markdown profile under `reports/research_profiles/` when `--save`
is used. The profile includes a lead summary, ICP fit rationale, personalization
angles, possible pain points, an outreach hook, missing research, and source
context.

## Outreach Orchestration

This is the first LangGraph orchestration milestone. It uses Groq for research,
writing, and review decisions, with LangGraph coordinating the node flow.

The workflow runs:

1. **Research** — retrieve lead memory and ask Groq to build a `ResearchProfile`.
2. **Write** — ask Groq to generate a first-touch `OutreachMessageDraft`.
3. **Review** — ask Groq to score, approve, or request revisions.

```bash
python -m ai_sdr.outreach.workflow "AI founder" --region germany --save
```

This writes a Markdown run artifact under `reports/outreach_runs/` when `--save`
is used. The artifact contains the research profile, message draft, review
checks, and reviewer feedback.

## Reply Classification

The reply classifier is the first reply-handling agent. It reads an inbound
prospect reply and returns structured intent, sentiment, urgency, confidence,
summary, and the recommended next action.

```bash
python -m ai_sdr.outreach.reply "Sounds interesting. Can you send more details?" --lead-id laura-schmidt --save
```

Supported intents include `interested`, `objection`, `not_now`, `unsubscribe`,
`out_of_office`, `referral`, `wrong_person`, `neutral`, and `unknown`.
Classifications saved with `--save` are written under
`reports/reply_classifications/`.

## Scheduling Agent

When a reply is classified as `interested` (or a `referral`), the scheduling
agent proposes a meeting. Candidate time slots are computed in Python on real
upcoming business days (no hallucinated dates), and Groq chooses the meeting
type, duration, agenda, and writes a short reply email offering those slots.

```bash
python -m ai_sdr.outreach.scheduling "Yes, I'd love a quick call next week" --lead-id laura-schmidt --lead-name Laura --save
```

For non-schedulable intents (for example `not_now` or `unsubscribe`), the agent
skips scheduling and explains why. Proposals saved with `--save` are written
under `reports/meeting_proposals/`.

## Demo UI

A FastAPI backend serves a single-page console for live demos and interaction.
It exposes the outreach workflow, reply triage, and scheduling agents over HTTP
and renders the results in the browser.

```bash
python -m uvicorn ai_sdr.api:app --reload
```

Then open http://127.0.0.1:8000. The header shows whether `GROQ_API_KEY` and
`PINECONE_API_KEY` are configured. Endpoints:

- `GET /api/health` — environment/config status.
- `POST /api/outreach` — research -> write -> review for a lead query (synchronous).
- `POST /api/reply` — classify an inbound reply.
- `POST /api/schedule` — triage a reply and, if interested, propose a meeting.
- `POST /api/evaluate/outreach` — score an outreach workflow run.
- `GET /api/observability/events` — read recent local observability events.
- `POST /api/jobs/outreach` — enqueue the outreach workflow as a background job.
- `GET /api/jobs/{job_id}` — poll a background job's status and result.

## Evaluation + Observability

The first evaluation slice scores a completed outreach run with Groq. It checks
message quality across six explicit metrics: research grounding,
personalization, clarity, tone, CTA quality, and risk control.

The evaluator returns a structured `OutreachEvaluation` with an overall score,
pass/fail, metric scores, risks, and recommendations. API calls also append
local JSONL events under `reports/observability/events.jsonl`, which the demo UI
can display from the Evaluation tab.

To evaluate a saved run JSON file from the CLI:

```bash
python -m ai_sdr.evaluation.outreach path/to/outreach_run.json --save
```

The current implementation is local and demo-friendly. Full adapters for RAGAS
datasets and Langfuse/Phoenix tracing remain planned.

## Async Workers (Redis + RQ)

The outreach workflow can run as a background job so the API stays responsive
during long LLM calls. Jobs are queued in Redis and processed by an RQ worker.
Redis and RQ are imported lazily, so the CLI and synchronous endpoints keep
working with no queue running; async endpoints return a clean `503` until a
Redis server is reachable.

Start Redis (for example via Docker), then run a worker:

```bash
docker run -p 6379:6379 redis:7        # or: brew services start redis
python -m ai_sdr.jobs.worker --simple  # --simple avoids fork issues on macOS
```

Enqueue a job and poll it from the API:

```bash
curl -s -X POST http://127.0.0.1:8000/api/jobs/outreach \
  -H 'Content-Type: application/json' \
  -d '{"query": "AI founder", "region": "germany"}'
# -> {"job_id": "...", "status": "queued"}

curl -s http://127.0.0.1:8000/api/jobs/<job_id>
# -> {"job_id": "...", "status": "finished", "result": {...}}
```

In the demo UI, tick **Run as background job (Redis worker)** on the Outreach
tab to enqueue the job and watch it move from `queued` to `started` to
`finished` live. Configure the connection with `REDIS_URL` (defaults to
`redis://localhost:6379/0`).

## Next Steps

- Add RAGAS dataset-backed evaluations and Langfuse/Phoenix tracing adapters.
- Dockerize the API, worker, and dependencies for one-command deployment.
