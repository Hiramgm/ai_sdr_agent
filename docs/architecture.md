# Architecture

This document shows both the **target system** and the **current build**. The diagrams use Mermaid, which renders automatically on GitHub and in most editors.

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

## Ingestion Build (Implemented)

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

## Data Flow (Ingestion)

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

## How Milestones Map To The Diagram

| Status | Component |
| --- | --- |
| Built | Ingestion + enrichment + ICP scoring |
| Built | PostgreSQL + MongoDB storage |
| Planned | Pinecone vector memory + research agent (RAG) |
| Planned | LangGraph outreach workflow |
| Planned | Reply + scheduling agents + Redis async workers |
| Planned | RAGAS evaluation + Langfuse/Phoenix observability |
| Planned | Docker + cloud deployment + dashboard |
