from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_sdr.config import SETTINGS, Settings
from ai_sdr.schemas import Lead


@dataclass(frozen=True)
class LeadMemoryRecord:
    """A lead converted into the text + metadata Pinecone stores and searches."""

    lead_id: str
    text: str
    metadata: dict[str, str | int]

    def to_pinecone_record(self, text_field: str) -> dict[str, str | int]:
        return {
            "_id": self.lead_id,
            text_field: self.text,
            **self.metadata,
        }


def build_lead_memory_record(lead: Lead) -> LeadMemoryRecord:
    """Turn one enriched lead into searchable research context."""
    reasons = "; ".join(lead.icp_reasons) if lead.icp_reasons else "No ICP reasons recorded."
    text = "\n".join(
        [
            f"Lead: {lead.full_name}",
            f"Title: {lead.title}",
            f"Company: {lead.company}",
            f"Company domain: {lead.company_domain or 'unknown'}",
            f"Industry: {lead.industry or 'unknown'}",
            f"Location: {lead.location or 'unknown'}",
            f"Region: {lead.region or 'unknown'}",
            f"Seniority: {lead.seniority or 'unknown'}",
            f"ICP score: {lead.icp_score}",
            f"ICP reasons: {reasons}",
            f"Source: {lead.source}",
        ]
    )

    return LeadMemoryRecord(
        lead_id=lead.lead_id,
        text=text,
        metadata={
            "lead_id": lead.lead_id,
            "full_name": lead.full_name,
            "title": lead.title,
            "company": lead.company,
            "company_domain": lead.company_domain,
            "industry": lead.industry,
            "region": lead.region,
            "seniority": lead.seniority,
            "icp_score": lead.icp_score,
            "source": lead.source,
        },
    )


def build_lead_memory_records(leads: list[Lead]) -> list[LeadMemoryRecord]:
    return [build_lead_memory_record(lead) for lead in leads]


class PineconeLeadMemory:
    """Pinecone-backed memory for enriched leads.

    This expects a Pinecone index configured for integrated embeddings, with its
    field map pointing at the same text field used here.
    """

    def __init__(self, settings: Settings = SETTINGS) -> None:
        if not settings.pinecone_api_key:
            raise ValueError("PINECONE_API_KEY is required to index lead memory.")

        try:
            from pinecone import Pinecone
        except ImportError as error:
            raise RuntimeError(
                "Install the Pinecone SDK before using --index-memory: "
                ".venv/bin/python -m pip install -r requirements.txt"
            ) from error

        self.namespace = settings.pinecone_namespace
        self.text_field = settings.pinecone_text_field
        self._index = Pinecone(api_key=settings.pinecone_api_key).Index(
            settings.pinecone_index
        )

    def upsert_leads(self, leads: list[Lead]) -> int:
        records = [
            record.to_pinecone_record(self.text_field)
            for record in build_lead_memory_records(leads)
        ]
        if not records:
            return 0

        self._index.upsert_records(namespace=self.namespace, records=records)
        return len(records)

    def search(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> Any:
        return self._index.search(
            namespace=self.namespace,
            inputs={"text": query},
            top_k=top_k,
            filter=metadata_filter,
            fields=[
                self.text_field,
                "lead_id",
                "full_name",
                "title",
                "company",
                "industry",
                "region",
                "seniority",
                "icp_score",
            ],
        )

