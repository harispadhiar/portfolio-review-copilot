---
title: Portfolio Review Copilot
emoji: 🗂️
colorFrom: indigo
colorTo: yellow
sdk: gradio
sdk_version: "6.22.0"
python_version: "3.12"
app_file: app.py
pinned: false
---

# Portfolio Review Copilot (RAG)

A RAG prototype that helps financial advisors check whether a product, fund, or portfolio
aligns with a client's profile — grounded strictly in uploaded documents, with a
compliance-aware structured verdict instead of free-text chat.

Built on LangChain + Groq + FAISS + Gradio: ingest -> chunk -> embed -> retrieve ->
generate, plus document-type tagging, a missing-document pre-flight check, and
Pydantic-enforced structured output.

## Key design choices

| Choice | Why |
|---|---|
| Doc-type tagging | Docs tagged as factsheet / risk disclosure / suitability policy / client profile / fee disclosure / objective statement / advisory note, so citations are type-aware |
| Structured output | `PortfolioReview` object: verdict, reasoning, missing info, sources — not a free-text answer |
| Compliance-framed system prompt | Grounding-only, no assumed client facts, "unclear" as a valid verdict, no directive language |
| Pre-flight gap detection | Flags missing core document types before the LLM even runs |
| Hybrid retrieval | FAISS dense + BM25 sparse, fused, then cross-encoder reranked — not dense similarity search alone |

## Why hybrid retrieval instead of plain FAISS similarity search

Dense-only similarity search is a reasonable default for general documents but a known
weak spot for finance. Financial text is dense with exact
identifiers — fund names, ISIN codes, fee percentages, clause numbers — and embedding
models tend to smooth these into "semantically close but factually wrong" matches. A 2026
benchmark on mixed text/table financial documents found plain BM25 keyword search actually
outperformed dense retrieval alone on this kind of content.

This project retrieves via `EnsembleRetriever` (from `langchain-classic`), fusing:
- **Dense** — FAISS over `sentence-transformers/all-MiniLM-L6-v2` embeddings, for
  paraphrased/semantic matches ("aggressive growth" ~ "high risk equity exposure").
- **Sparse** — BM25, for exact-term matches (a specific fund name, "1.75%", "TER").

Both retrieve a candidate pool of 20, get fused, then a cross-encoder
(`cross-encoder/ms-marco-MiniLM-L-6-v2`) reranks down to the final 5 chunks sent to the
LLM — the "retrieve 20, rerank to 5" pattern that's become standard for production RAG in
2026. FAISS isn't replaced; it's one leg of the hybrid pipeline, which is the
finance-appropriate role for it.

**Tuning knobs in `rag_pipeline.py`**: `DENSE_WEIGHT`/`SPARSE_WEIGHT` (currently 0.4/0.6,
favoring exact-term matches), `CANDIDATE_K`/`FINAL_K`, and `RERANK_MODEL` (swap for a
finance-tuned reranker like `bge-reranker-v2-m3` if you outgrow the general-purpose default).

## Design

The UI uses a "case file" visual language suited to compliance review work rather than a
default Gradio look: an ink-navy + brass accent palette, a serif display face for headers
paired with a monospace face for data/labels, uploaded documents shown as a manifest
checklist (required vs. optional types called out), and verdicts rendered as a stamped
seal rather than plain text. All CSS lives in `app.py` (`CUSTOM_CSS`) — design tokens
(colors, doc-type accents) are defined near the top of the file if you want to retheme it.

## Setup

```bash
uv venv
uv pip install -r requirements.txt
cp .env.example .env   # add your GROQ_API_KEY (HF_TOKEN is optional)
uv run python app.py
```

Open http://127.0.0.1:7860

## Test it

`data/` has two scenarios, each with all 7 document types:

**`scenario_a_mismatch/`** — a conservative, near-retirement client (low risk tolerance,
short horizon, explicit loss limit) paired with an aggressive high-volatility equity fund.
1. Upload all 7 files from `data/scenario_a_mismatch/`.
2. Click "Build index".
3. Ask: `Is the Alpha Growth Equity Fund suitable for this client?`
4. Expect an "unsuitable" or "possibly suitable" verdict — the client risk profile,
   suitability policy, and even the advisor's own internal note point the same direction.

**`scenario_b_match/`** — a mid-career client with an 8-year horizon and moderate risk
tolerance, paired with a balanced fund whose risk profile and horizon line up.
1. Upload all 7 files from `data/scenario_b_match/`.
2. Click "Build index".
3. Ask: `Is the Balanced Growth Allocation Fund suitable for this client?`
4. Expect a "suitable" verdict with supporting reasoning.

**Missing-data path**: rebuild the index with one or two files removed from either scenario
(e.g. drop the client risk profile) — you should see it flagged under "Missing information".

See `SAMPLE_QUESTIONS.md` for a broader set of test prompts — including hallucination
guardrail checks, policy-compliance questions, and cross-document reasoning tests.

## Files

- `loaders.py` — file loading (PDF/DOCX/CSV/XLSX/TXT) + keyword-based doc-type classifier
- `schema.py` — `DocType`, `Verdict`, `PortfolioReview` Pydantic models
- `prompts.py` — system prompt encoding the suitability-review rules + context formatter
- `rag_pipeline.py` — chunking, hybrid FAISS+BM25 retrieval, reranking, structured generation, gap detection
- `app.py` — Gradio UI (upload -> build index -> ask -> verdict card)
- `main.py` — entry point

## Known prototype limits (next steps)

- Doc-type classification is keyword-based, not a trained classifier — fine for a
  prototype, will misfire on oddly-named or ambiguous files.
- No conversation memory — each question is a fresh retrieval.
- `missing_core_doc_types()` only checks presence/absence of doc types, not whether a
  present document actually contains the specific field needed (e.g., a risk profile
  file with no stated risk tolerance still counts as "present").
- Structured output via `with_structured_output` requires a Groq model with tool-calling
  support (default: `llama-3.3-70b-versatile`). Swap `GROQ_MODEL` in `.env` if needed.
- The reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`) is a general-purpose model, not
  finance-tuned. It's a solid prototype default; a finance-specific reranker would likely
  improve precision further on dense numeric/tabular content.
- `sentence-transformers` (used for both embeddings and reranking) pulls in `torch`, which
  is a multi-GB install — make sure you have disk space before `uv pip install -r requirements.txt`.