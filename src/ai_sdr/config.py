from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = ROOT_DIR / "reports"

# Load variables from a local .env file (if present) into the environment so
# that the settings below can read them. Secrets stay in .env, never in code.
load_dotenv(ROOT_DIR / ".env")


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
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
    pinecone_index: str = os.getenv("PINECONE_INDEX", "ai-sdr-leads")
    pinecone_namespace: str = os.getenv("PINECONE_NAMESPACE", "leads")
    pinecone_text_field: str = os.getenv("PINECONE_TEXT_FIELD", "text")
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    postgres_url: str = os.getenv("POSTGRES_URL", "postgresql://localhost:5432/ai_sdr")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    observability_sink: str = os.getenv("OBSERVABILITY_SINK", "local")
    langfuse_host: str = os.getenv("LANGFUSE_HOST", "")
    langfuse_public_key: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    langfuse_secret_key: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    phoenix_endpoint: str = os.getenv("PHOENIX_ENDPOINT", "")


SETTINGS = Settings()
ICP = ICPConfig()
