"""
Pydantic schemas for the Portfolio Review Copilot.

Two jobs:
1. DOC_TYPES — the fixed vocabulary of document types the prompt spec calls for.
2. PortfolioReview — the structured object the LLM must return, enforced via
   ChatGroq(...).with_structured_output(PortfolioReview) so the UI never has to
   regex-parse free text.
"""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class DocType(str, Enum):
    FACTSHEET = "Product factsheet"
    RISK_DISCLOSURE = "Risk disclosure document"
    SUITABILITY_POLICY = "Suitability policy"
    CLIENT_RISK_PROFILE = "Client risk profile"
    FEE_DISCLOSURE = "Fee and charges disclosure"
    OBJECTIVE_STATEMENT = "Investment objective statement"
    ADVISORY_NOTE = "Internal advisory note"
    UNKNOWN = "Unclassified document"


class Verdict(str, Enum):
    SUITABLE = "suitable"
    POSSIBLY_SUITABLE = "possibly suitable"
    UNSUITABLE = "unsuitable"
    UNCLEAR = "unclear"


class SourceRef(BaseModel):
    document_name: str = Field(description="Filename of the source document")
    doc_type: str = Field(description="Document type as classified, e.g. 'Client risk profile'")
    excerpt: str = Field(description="Short supporting excerpt or paraphrase, under 25 words")


class PortfolioReview(BaseModel):
    verdict: Verdict = Field(description="One of: suitable, possibly suitable, unsuitable, unclear")
    reasoning: List[str] = Field(description="Short bullet points grounded strictly in retrieved context")
    missing_information: List[str] = Field(
        default_factory=list,
        description="Required fields/documents not found in the retrieved context. Empty list if nothing is missing."
    )
    sources: List[SourceRef] = Field(default_factory=list, description="Document references backing the verdict")
    uncertainty_note: str = Field(
        default="",
        description="Explicit statement of uncertainty or limitation, if any. Empty string if none."
    )
