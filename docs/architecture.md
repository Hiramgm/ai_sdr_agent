# Architecture

This document shows both the **target system** and the **current Day 1 build**. The diagrams use Mermaid, which renders automatically on GitHub and in most editors.

## Target System (Full Build)

```mermaid
flowchart TB
    user[User / Business] -->|defines ICP| api[FastAPI Backend]

    subgraph Ingestion
        scraper[Scraper Workers\nPlaywright + BeautifulSoup]
        enrich[Enrichment + ICP Scoring]
    end

    subgraph Queue
        redis[(Redis)]
        workers[Async Workers\nRQ]
    end

    subgraph Storage
        postgres[(PostgreSQL\nleads, campaigns, meetings)]
        mongo[(MongoDB\nraw data, message logs)]
        pinecone[(Pinecone\nlead memory + embeddings)]
    end

    subgraph Orchestration[LangGraph Orchestration]
        research[Research Agent]
        writer[Writer Agent]
        reviewer[Reviewer Agent]
        reply[Reply Agent]
        scheduler[Scheduling Agent]
    end

    subgraph LLM
        groq[Groq API\nopen-source models]
    end

    subgraph Quality
        ragas[RAGAS Evaluation]
        obs[Langfuse / Phoenix\nObservability]
    end

    api --> scraper --> enrich --> redis --> workers
    workers --> postgres
    workers --> mongo
    enrich --> pinecone

    api --> Orchestration
    research --> pinecone
    research --> groq
    writer --> groq
    reviewer --> groq
    reply --> groq
    scheduler --> postgres

    Orchestration --> ragas
    Orchestration --> obs

    api --> dashboard[Dashboard / Frontend]
```

## Day 1 Build (Implemented)

```mermaid
flowchart LR
    source[Source\nsample or JSON/CSV file] --> raw[RawLead objects]
    raw --> enrich[Enrichment\ndomain, seniority, region]
    enrich --> score[ICP Scoring\nrule-based + reasons]
    score --> store[(JSONL Storage)]
    store --> rawfile[data/raw/leads_raw.jsonl]
    store --> procfile[data/processed/leads.jsonl]
    score --> report[reports/ingestion_report.md]
```

## Data Flow (Day 1)

```mermaid
sequenceDiagram
    participant CLI as pipeline.py
    participant SRC as ingestion.sources
    participant ENR as ingestion.enrich
    participant ST as storage
    participant RP as reporting

    CLI->>SRC: load_raw_leads(source, input)
    SRC-->>CLI: list[RawLead]
    CLI->>ENR: enrich_leads(raws, ICP)
    ENR-->>CLI: list[Lead] (scored)
    CLI->>ST: write raw + enriched JSONL
    CLI->>RP: write_report(leads)
    RP-->>CLI: ingestion_report.md
```

## How The Days Map To The Diagram

| Day | Component added |
| --- | --- |
| 1 | Ingestion + enrichment + ICP scoring |
| 2 | PostgreSQL + MongoDB storage |
| 3 | Pinecone vector memory + research agent (RAG) |
| 4 | LangGraph outreach workflow |
| 5 | Reply + scheduling agents + Redis async workers |
| 6 | RAGAS evaluation + Langfuse/Phoenix observability |
| 7 | Docker + cloud deployment + dashboard |
