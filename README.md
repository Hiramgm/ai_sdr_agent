# AI SDR — Autonomous Sales Development Rep

An open-source-first AI Sales Development Rep. It finds leads, researches them, scores fit, writes personalized outreach, handles replies, and books meetings, all through an orchestrated multi-agent workflow.

This repository is built in public, one day at a time, as a production-style project covering ingestion, RAG, agentic orchestration, evaluation, observability, and cloud deployment.

## Product Vision

Businesses define their ideal customer. The system then:

1. Ingests and enriches matching leads.
2. Scores each lead against the Ideal Customer Profile (ICP).
3. Researches each lead for personalization context.
4. Writes a tailored first message and follow-up sequence.
5. Handles replies (interested, objection, not now, book a meeting).
6. Tracks pipeline, quality, and observability metrics.

## Architecture (Target)

See [docs/architecture.md](docs/architecture.md) for full diagrams (target system, Day 1 build, and data flow).

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

## Build Plan

- Day 1: Lead ingestion + enrichment + ICP scoring (this commit).
- Day 2: Databases — PostgreSQL (leads, campaigns) + MongoDB (raw, logs).
- Day 3: Pinecone vector memory + research agent (RAG, Groq).
- Day 4: LangGraph outreach workflow (research -> write -> review -> send).
- Day 5: Reply handling + scheduling agent + Redis async workers.
- Day 6: RAGAS message-quality evals + Langfuse/Phoenix observability.
- Day 7: Dockerize, deploy, dashboard, README polish, demo.

## Day 1: What Is Implemented

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

## Next Steps

- Add database persistence (PostgreSQL + MongoDB).
- Add Pinecone-backed lead memory.
- Replace rule-based ICP scoring with an LLM scoring agent.
- Build the LangGraph outreach workflow.
