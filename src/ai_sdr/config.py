from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = ROOT_DIR / "reports"


@dataclass(frozen=True)
class ICPConfig:
    """Ideal Customer Profile used to score lead fit."""

    target_titles: list[str] = field(
        default_factory=lambda: [
            "head of marketing",
            "vp marketing",
            "growth",
            "demand generation",
            "founder",
            "ceo",
            "cto",
            "head of sales",
        ]
    )
    target_seniorities: list[str] = field(
        default_factory=lambda: ["head", "vp", "director", "c-level", "founder"]
    )
    target_regions: list[str] = field(
        default_factory=lambda: ["europe", "remote", "uk", "germany", "finland"]
    )
    target_industries: list[str] = field(
        default_factory=lambda: ["saas", "software", "ai", "technology"]
    )


@dataclass(frozen=True)
class Settings:
    """Runtime settings. Secrets are read from the environment, never hardcoded."""

    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
    pinecone_index: str = os.getenv("PINECONE_INDEX", "ai-sdr-leads")
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    postgres_url: str = os.getenv("POSTGRES_URL", "postgresql://localhost:5432/ai_sdr")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")


SETTINGS = Settings()
ICP = ICPConfig()
