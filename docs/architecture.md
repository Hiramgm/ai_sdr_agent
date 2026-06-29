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

## Current Build (Implemented)

```mermaid
flowchart LR
    source[Source\nsample or JSON/CSV file] --> raw[RawLead objects]
    raw --> enrich[Enrichment\ndomain, seniority, region]
    enrich --> score[ICP Scoring\nrule-based + reasons]
    score --> store[(JSONL Storage)]
    store --> rawfile[data/raw/leads_raw.jsonl]
    store --> procfile[data/processed/leads.jsonl]
    score --> report[reports/ingestion_report.md]
    score -. --index-memory .-> pinecone[(Pinecone\nlead memory)]
    query[Search query] -. memory.search .-> pinecone
    pinecone -. matches .-> results[Relevant lead records]
    results -. Groq research .-> profile[Research profile]
    profile -. Groq writer .-> draft[Message draft]
    draft -. Groq reviewer .-> review[Review result]
    review -. save .-> run[Outreach run artifact]
    inbound[Inbound reply] -. Groq reply classifier .-> replyclass[Reply classification]
    replyclass -. save .-> replyartifact[Reply classification artifact]
    replyclass -. interested/referral .-> scheduler[Scheduling agent\nGroq + business-day slots]
    scheduler -. save .-> meetingartifact[Meeting proposal artifact]
    api[FastAPI demo API + web UI] -. calls .-> profile
    api -. calls .-> replyclass
    api -. calls .-> scheduler
    api -. enqueue .-> redis[(Redis queue)]
    redis -. dequeue .-> worker[RQ worker]
    worker -. runs .-> profile
    api -. poll status .-> redis
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
| Built | Pinecone vector memory + Groq research agent (RAG) |
| Built | LangGraph outreach workflow (`research -> write -> review`) |
| Built | Reply classification agent |
| Built | Scheduling agent (meeting proposals) |
| Built | FastAPI demo API + web UI console |
| Built | Redis + RQ async workers (background outreach jobs) |
| Planned | RAGAS evaluation + Langfuse/Phoenix observability |
| Planned | Docker + cloud deployment + dashboard |

## TODOs / Deferred Polish

- Add LLM-based query parsing for lead-memory search after the full outreach
  pipeline is built. The current search command supports explicit metadata
  filters (`--region`, `--industry`, `--seniority`, `--min-icp-score`) for
  debuggability. Later, Groq can extract those filters from natural-language
  queries such as "AI founder in Germany" and pass them into the same retrieval
  layer.
- Background outreach jobs now run behind Redis + RQ workers. Next, fold reply
  triage + scheduling into the LangGraph workflow once the send/wait boundary is
  added, and move ingestion onto the same queue.
