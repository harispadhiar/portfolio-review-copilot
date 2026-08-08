"""
File loading + document-type classification.

Supports PDF, DOCX, CSV, XLSX, and TXT, reusing LangChain's community loaders
rather than hand-rolling extraction (vibe-coding ladder step 3: the library
already does this).

Doc-type classification is a keyword heuristic over filename + first-chunk
content. This is a prototype, not a document-classification model — good
enough to route citations correctly, and cheap enough to run per-file at
ingest time. Swap for a zero-shot classifier later if precision matters.
"""

import os
from typing import List

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    CSVLoader,
    UnstructuredExcelLoader,
    TextLoader,
)

from schema import DocType

# Keyword -> DocType. Checked against filename first (cheap, usually reliable
# since advisors name files sensibly), then document body if filename is unclear.
DOC_TYPE_KEYWORDS = {
    DocType.FACTSHEET: ["factsheet", "fact sheet", "fund fact", "ksfs"],
    DocType.RISK_DISCLOSURE: ["risk disclosure", "risk warning", "risk statement"],
    DocType.SUITABILITY_POLICY: ["suitability policy", "suitability assessment", "suitability framework"],
    DocType.CLIENT_RISK_PROFILE: ["client risk profile", "client profile", "risk questionnaire", "kyc"],
    DocType.FEE_DISCLOSURE: ["fee", "charges", "expense ratio", "commission disclosure"],
    DocType.OBJECTIVE_STATEMENT: ["investment objective", "mandate", "investment policy statement", "ips"],
    DocType.ADVISORY_NOTE: ["advisory note", "internal note", "meeting note", "advisor note"],
}

LOADERS_BY_EXT = {
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".csv": CSVLoader,
    ".xlsx": UnstructuredExcelLoader,
    ".txt": TextLoader,
}


def classify_doc_type(filename: str, sample_text: str) -> DocType:
    haystack = f"{filename} {sample_text[:1500]}".lower()
    for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
        if any(kw in haystack for kw in keywords):
            return doc_type
    return DocType.UNKNOWN


def load_file(file_path: str) -> List[Document]:
    """Load a single file and tag every resulting Document with source + doc_type metadata."""
    ext = os.path.splitext(file_path)[1].lower()
    loader_cls = LOADERS_BY_EXT.get(ext)
    if loader_cls is None:
        raise ValueError(f"Unsupported file type: {ext}")

    docs = loader_cls(file_path).load()
    if not docs:
        raise ValueError(f"No text extracted from {os.path.basename(file_path)}")

    filename = os.path.basename(file_path)
    sample_text = docs[0].page_content
    doc_type = classify_doc_type(filename, sample_text)

    for d in docs:
        d.metadata["source"] = filename
        d.metadata["doc_type"] = doc_type.value

    return docs


def load_files(file_paths: List[str]) -> List[Document]:
    all_docs: List[Document] = []
    errors: List[str] = []
    for path in file_paths:
        try:
            all_docs.extend(load_file(path))
        except Exception as e:
            errors.append(f"{os.path.basename(path)}: {e}")
    if errors and not all_docs:
        raise ValueError("All files failed to load:\n" + "\n".join(errors))
    return all_docs
