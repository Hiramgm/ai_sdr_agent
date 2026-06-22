# Lead Ingestion Report

Total leads ingested: 5
Qualified leads (ICP score >= 60): 4

## Seniority Breakdown

- **head**: 1
- **c-level**: 1
- **vp**: 1
- **manager**: 1
- **individual**: 1

## Region Breakdown

- **uk**: 2
- **germany**: 1
- **finland**: 1
- **remote**: 1

## Top Leads by ICP Score

- **Laura Schmidt** — Head of Marketing at Northwind SaaS
  - ICP score: 100
  - Region: germany | Seniority: head
  - Why: Title matches target buyer persona; Seniority 'head' is a decision maker; Region 'germany' is in target market; Industry 'SaaS' fits ICP
- **James Carter** — Founder & CEO at Flowmetrics
  - ICP score: 100
  - Region: uk | Seniority: c-level
  - Why: Title matches target buyer persona; Seniority 'c-level' is a decision maker; Region 'uk' is in target market; Industry 'AI' fits ICP
- **Sofia Virtanen** — VP of Growth at Helsinki Analytics
  - ICP score: 100
  - Region: finland | Seniority: vp
  - Why: Title matches target buyer persona; Seniority 'vp' is a decision maker; Region 'finland' is in target market; Industry 'Software' fits ICP
- **Daniel Osei** — Demand Generation Manager at BrightCloud
  - ICP score: 75
  - Region: remote | Seniority: manager
  - Why: Title matches target buyer persona; Region 'remote' is in target market; Industry 'Technology' fits ICP
- **Priya Nair** — Office Administrator at Local Dental Clinic
  - ICP score: 20
  - Region: uk | Seniority: individual
  - Why: Region 'uk' is in target market

## Pipeline Notes

- Raw leads are stored in `data/raw/leads_raw.jsonl`.
- Enriched and scored leads are stored in `data/processed/leads.jsonl`.
- ICP scoring is rule-based today and will be augmented with an LLM agent in a later day.