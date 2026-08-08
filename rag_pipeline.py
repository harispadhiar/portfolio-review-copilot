"""
RAG pipeline for the Portfolio Review Copilot.

Retrieval is hybrid, not dense-only. Financial documents are dense with exact
identifiers (fund names, ISIN/SEDOL codes, percentages, clause numbers) that
embedding models tend to smooth over into "semantically close but wrong"
matches. A 2026 benchmark on mixed text/table financial documents found plain
BM25 keyword search actually outperformed dense retrieval alone on this kind
of content (Strich et al., 2026) — the fix the field converged on is hybrid
retrieval (dense + BM25, fused) followed by reranking, not picking one method.

Pipeline: LangChain text splitter -> HuggingFace embeddings -> FAISS (dense)
          + BM25 (sparse) -> EnsembleRetriever fusion -> cross-encoder rerank
          -> Groq LLM structured generation.

FAISS itself isn't the problem and isn't replaced — using it as the dense leg
of a hybrid retriever is standard practice. What's finance-inappropriate is
relying on dense similarity search alone.
"""

import os
from typing import List, Tuple

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_groq import ChatGroq
from sentence_transformers import CrossEncoder

from loaders import load_files
from schema import PortfolioReview, DocType
from prompts import SYSTEM_PROMPT, format_context

load_dotenv()

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# General-purpose reranker. Swap for a finance-tuned or stronger reranker
# (e.g. bge-reranker-v2-m3) later if precision on numeric/tabular content
# needs to improve -- this is the "good enough for a prototype" default.
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120

# Retrieve a wide candidate pool from hybrid search, then rerank down to a
# small, high-precision set before it ever reaches the LLM. This is the
# "retrieve 20, rerank to 5" pattern that 2026 production RAG converged on.
CANDIDATE_K = 20
FINAL_K = 5

# Fusion weights for dense vs sparse. Financial text leans on exact terms, so
# BM25 gets slightly more weight than the 50/50 default -- tune against your
# own query set if you have one.
DENSE_WEIGHT = 0.4
SPARSE_WEIGHT = 0.6

# Documents a suitability review should ideally have. Used only to flag gaps
# up front — retrieval still runs on whatever was actually uploaded.
CORE_DOC_TYPES = [
    DocType.CLIENT_RISK_PROFILE,
    DocType.FACTSHEET,
    DocType.RISK_DISCLOSURE,
    DocType.OBJECTIVE_STATEMENT,
]


class PortfolioReviewIndex:
    def __init__(self):
        self.vectorstore: FAISS | None = None
        self.hybrid_retriever: EnsembleRetriever | None = None
        self.reranker: CrossEncoder | None = None
        self.doc_types_present: set[str] = set()

    def build(self, file_paths: List[str]) -> str:
        docs = load_files(file_paths)
        if not docs:
            raise ValueError("No text was extracted from uploaded files.")

        self.doc_types_present = {d.metadata.get("doc_type") for d in docs}

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        )
        chunks = splitter.split_documents(docs)
        if not chunks:
            raise ValueError("Documents were loaded, but no chunks were created.")

        # Dense leg: FAISS over HF embeddings.
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.vectorstore = FAISS.from_documents(chunks, embeddings)
        dense_retriever = self.vectorstore.as_retriever(search_kwargs={"k": CANDIDATE_K})

        # Sparse leg: BM25 over the same chunks, for exact-term matches
        # (fund names, fee percentages, clause numbers) dense embeddings miss.
        sparse_retriever = BM25Retriever.from_documents(chunks)
        sparse_retriever.k = CANDIDATE_K

        # Fuse both via reciprocal rank fusion.
        self.hybrid_retriever = EnsembleRetriever(
            retrievers=[dense_retriever, sparse_retriever],
            weights=[DENSE_WEIGHT, SPARSE_WEIGHT],
        )

        if self.reranker is None:
            self.reranker = CrossEncoder(RERANK_MODEL)

        type_summary = ", ".join(sorted(self.doc_types_present)) or "none detected"
        return f"Indexed {len(docs)} document(s) into {len(chunks)} chunks.\nDetected types: {type_summary}"

    def missing_core_doc_types(self) -> List[str]:
        return [t.value for t in CORE_DOC_TYPES if t.value not in self.doc_types_present]

    def retrieve(self, question: str) -> List[Document]:
        if self.hybrid_retriever is None:
            raise ValueError("Index not built yet. Upload documents first.")

        candidates = self.hybrid_retriever.invoke(question)
        if not candidates:
            return []

        # Cross-encoder rerank: score each (question, chunk) pair directly,
        # rather than trusting the fused rank order alone.
        pairs = [(question, c.page_content) for c in candidates]
        scores = self.reranker.predict(pairs)
        ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)
        return [doc for doc, _score in ranked[:FINAL_K]]

    def review(self, question: str) -> Tuple[PortfolioReview, List[Document]]:
        retrieved = self.retrieve(question)
        context = format_context(retrieved)

        llm = ChatGroq(model=GROQ_MODEL, temperature=0)
        structured_llm = llm.with_structured_output(PortfolioReview)

        prompt = SYSTEM_PROMPT.format(context=context, question=question)
        result: PortfolioReview = structured_llm.invoke(prompt)

        # Pre-flight gaps aren't guaranteed to be in the LLM's own missing list
        # (it only sees what was retrieved, not the full corpus) — merge them in.
        preflight_gaps = [g for g in self.missing_core_doc_types() if g not in result.missing_information]
        result.missing_information = result.missing_information + preflight_gaps

        return result, retrieved
