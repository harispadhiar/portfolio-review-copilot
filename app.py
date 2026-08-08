"""
Gradio UI. Designed around a "case file" metaphor suited to compliance review work:
uploaded documents read as a manifest checklist, a verdict renders as a stamped seal
(the way a reviewed file gets marked), and sources render as document-type-coded chips
so an advisor can see at a glance which document backs which claim.
"""

import html as html_lib

import gradio as gr

from rag_pipeline import PortfolioReviewIndex
from schema import PortfolioReview, DocType

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

INK = "#1B2A4A"
INK_SOFT = "#4A5578"
PAPER = "#F6F4EF"
PANEL = "#FFFFFF"
BRASS = "#B08D57"
BRASS_SOFT = "#EFE6D8"
LINE = "#E3DFD4"

VERDICT_STYLE = {
    "suitable": ("SUITABLE", "\u2713", "#2F6F52", "#E7F2EA"),
    "possibly suitable": ("POSSIBLY SUITABLE", "\u25b3", "#B4791F", "#FBF0DE"),
    "unsuitable": ("UNSUITABLE", "\u2715", "#A23B32", "#FAEAE7"),
    "unclear": ("UNCLEAR", "?", "#5B6472", "#EDEEF0"),
}

# One accent per document type, used for chip borders in the manifest and source list.
DOC_TYPE_COLOR = {
    DocType.FACTSHEET.value: "#2F7A73",
    DocType.RISK_DISCLOSURE.value: "#B4532B",
    DocType.SUITABILITY_POLICY.value: "#3F4E9C",
    DocType.CLIENT_RISK_PROFILE.value: "#7A4B8A",
    DocType.FEE_DISCLOSURE.value: "#8A7B2F",
    DocType.OBJECTIVE_STATEMENT.value: "#3E7C8C",
    DocType.ADVISORY_NOTE.value: "#55636B",
    DocType.UNKNOWN.value: "#8B8B8B",
}

REQUIRED_TYPES = [
    DocType.CLIENT_RISK_PROFILE,
    DocType.FACTSHEET,
    DocType.RISK_DISCLOSURE,
    DocType.OBJECTIVE_STATEMENT,
]
OPTIONAL_TYPES = [
    DocType.SUITABILITY_POLICY,
    DocType.FEE_DISCLOSURE,
    DocType.ADVISORY_NOTE,
]

CUSTOM_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Lora:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');

.gradio-container {{
    background: {PAPER} !important;
    font-family: 'Inter', ui-sans-serif, system-ui, sans-serif !important;
    color: {INK} !important;
}}

.pr-hero {{
    padding: 4px 4px 18px 4px;
    border-bottom: 1px solid {LINE};
    margin-bottom: 18px;
}}
.pr-eyebrow {{
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: {BRASS};
    margin-bottom: 6px;
}}
.pr-title {{
    font-family: 'Lora', serif;
    font-weight: 700;
    font-size: 28px;
    color: {INK};
    margin: 0 0 6px 0;
}}
.pr-subtitle {{
    font-size: 14px;
    color: {INK_SOFT};
    max-width: 640px;
    line-height: 1.5;
    margin: 0;
}}

.pr-card {{
    background: {PANEL} !important;
    border: 1px solid {LINE} !important;
    border-radius: 14px !important;
    padding: 4px !important;
}}
.pr-card .styler {{
    --layout-gap: 14px !important;
    --form-gap-width: 14px !important;
}}
.pr-card .block {{ margin-bottom: 4px; }}

/* Example question chips */
.gradio-container table.dataset,
.gradio-container .dataset {{
    border-color: {LINE} !important;
}}
.gradio-container .dataset button,
.gradio-container table.dataset td {{
    background: {BRASS_SOFT} !important;
    border: 1px solid {BRASS} !important;
    border-radius: 8px !important;
    color: {INK} !important;
    font-size: 13px !important;
}}
.gradio-container .dataset button:hover {{
    background: #E4D6BE !important;
}}

.pr-panel-label {{
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {INK_SOFT};
    padding: 14px 16px 0 16px;
}}

/* Document manifest checklist */
.pr-manifest {{ padding: 6px 16px 16px 16px; }}
.pr-manifest-empty {{
    font-size: 13px;
    color: {INK_SOFT};
    font-style: italic;
    padding: 8px 0;
}}
.pr-chip-row {{ display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }}
.pr-chip {{
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 7px 10px;
    border-radius: 8px;
    border: 1px solid {LINE};
    background: #FAF9F5;
    font-size: 13px;
}}
.pr-chip.present {{ background: #FFFFFF; }}
.pr-chip.missing {{ opacity: 0.55; border-style: dashed; }}
.pr-chip-dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
.pr-chip-label {{ flex: 1; color: {INK}; }}
.pr-chip-req {{
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 9px;
    letter-spacing: 0.06em;
    color: {BRASS};
    border: 1px solid {BRASS};
    border-radius: 4px;
    padding: 1px 5px;
}}

/* Verdict stamp */
.pr-stamp-row {{ display: flex; justify-content: flex-start; margin: 6px 0 20px 0; }}
.pr-stamp {{
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 10px 20px;
    border: 3px double var(--stamp-color);
    border-radius: 10px;
    transform: rotate(-1.5deg);
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-weight: 600;
    font-size: 15px;
    letter-spacing: 0.08em;
    color: var(--stamp-color);
    background: var(--stamp-bg);
}}

.pr-section {{ margin-bottom: 20px; }}
.pr-section-label {{
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {BRASS};
    margin-bottom: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid {LINE};
}}
.pr-bullets {{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 7px; }}
.pr-bullets li {{
    position: relative;
    padding-left: 16px;
    font-size: 14px;
    line-height: 1.5;
    color: {INK};
}}
.pr-bullets li::before {{
    content: "\\2013";
    position: absolute;
    left: 0;
    color: {BRASS};
    font-weight: 600;
}}
.pr-bullets.missing li::before {{ content: "!"; color: #B4791F; }}
.pr-empty-note {{ font-size: 13px; color: {INK_SOFT}; font-style: italic; }}

.pr-sources {{ display: flex; flex-direction: column; gap: 8px; }}
.pr-source-chip {{
    border-left: 3px solid var(--src-color);
    background: #FAF9F5;
    border-radius: 0 8px 8px 0;
    padding: 8px 12px;
}}
.pr-source-type {{
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--src-color);
}}
.pr-source-doc {{ font-size: 12px; color: {INK_SOFT}; margin-left: 6px; }}
.pr-source-excerpt {{ font-size: 13px; color: {INK}; margin-top: 3px; line-height: 1.4; }}

.pr-callout {{
    border-left: 3px solid {BRASS};
    background: {BRASS_SOFT};
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    font-size: 13px;
    color: {INK};
    line-height: 1.5;
}}

.pr-placeholder {{
    padding: 30px 16px;
    text-align: center;
    color: {INK_SOFT};
    font-size: 13px;
}}

.pr-error {{
    padding: 12px 14px;
    border-radius: 8px;
    background: #FAEAE7;
    border-left: 3px solid #A23B32;
    color: #7A2A22;
    font-size: 13px;
}}

button.primary {{
    background: {INK} !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
}}
button.primary:hover {{ background: #2A3D66 !important; }}
"""


def _esc(text: str) -> str:
    return html_lib.escape(text or "")


def render_manifest(idx: PortfolioReviewIndex | None) -> str:
    if idx is None or not idx.doc_types_present:
        return (
            '<div class="pr-panel-label">Document manifest</div>'
            '<div class="pr-manifest"><div class="pr-manifest-empty">'
            "No documents indexed yet. Upload files and build the index."
            "</div></div>"
        )

    rows = []
    for t in REQUIRED_TYPES + OPTIONAL_TYPES:
        present = t.value in idx.doc_types_present
        color = DOC_TYPE_COLOR.get(t.value, "#8B8B8B")
        state_class = "present" if present else "missing"
        dot_color = color if present else LINE
        req_badge = '<span class="pr-chip-req">required</span>' if t in REQUIRED_TYPES else ""
        rows.append(
            f'<div class="pr-chip {state_class}">'
            f'<span class="pr-chip-dot" style="background:{dot_color}"></span>'
            f'<span class="pr-chip-label">{_esc(t.value)}</span>'
            f"{req_badge}"
            f"</div>"
        )

    return (
        '<div class="pr-panel-label">Document manifest</div>'
        f'<div class="pr-manifest"><div class="pr-chip-row">{"".join(rows)}</div></div>'
    )


def render_review(review: PortfolioReview) -> str:
    label, icon, color, bg = VERDICT_STYLE.get(
        review.verdict.value, (review.verdict.value.upper(), "", INK, PANEL)
    )
    stamp = (
        f'<div class="pr-stamp-row"><div class="pr-stamp" '
        f'style="--stamp-color:{color};--stamp-bg:{bg}">{icon} {label}</div></div>'
    )

    if review.reasoning:
        items = "".join(f"<li>{_esc(r)}</li>" for r in review.reasoning)
        reasoning_html = f'<ul class="pr-bullets">{items}</ul>'
    else:
        reasoning_html = '<div class="pr-empty-note">No reasoning returned.</div>'
    reasoning_section = (
        '<div class="pr-section"><div class="pr-section-label">Reasoning</div>'
        f"{reasoning_html}</div>"
    )

    if review.missing_information:
        items = "".join(f"<li>{_esc(m)}</li>" for m in review.missing_information)
        missing_html = f'<ul class="pr-bullets missing">{items}</ul>'
    else:
        missing_html = '<div class="pr-empty-note">None identified.</div>'
    missing_section = (
        '<div class="pr-section"><div class="pr-section-label">Missing information</div>'
        f"{missing_html}</div>"
    )

    if review.sources:
        chips = []
        for s in review.sources:
            color = DOC_TYPE_COLOR.get(s.doc_type, "#8B8B8B")
            chips.append(
                f'<div class="pr-source-chip" style="--src-color:{color}">'
                f'<span class="pr-source-type">{_esc(s.doc_type)}</span>'
                f'<span class="pr-source-doc">{_esc(s.document_name)}</span>'
                f'<div class="pr-source-excerpt">{_esc(s.excerpt)}</div>'
                f"</div>"
            )
        sources_html = f'<div class="pr-sources">{"".join(chips)}</div>'
    else:
        sources_html = '<div class="pr-empty-note">None returned.</div>'
    sources_section = (
        '<div class="pr-section"><div class="pr-section-label">Source references</div>'
        f"{sources_html}</div>"
    )

    callout = (
        f'<div class="pr-section"><div class="pr-callout">{_esc(review.uncertainty_note)}</div></div>'
        if review.uncertainty_note
        else ""
    )

    return stamp + reasoning_section + missing_section + sources_section + callout


def build_index(files):
    if not files:
        return (
            '<div class="pr-error">Upload at least one document first.</div>',
            render_manifest(None),
            None,
        )
    idx = PortfolioReviewIndex()
    try:
        idx.build([f.name for f in files])
    except Exception as e:
        return f'<div class="pr-error">Error while building index: {_esc(str(e))}</div>', render_manifest(None), None

    gaps = idx.missing_core_doc_types()
    if gaps:
        status = (
            f'<div class="pr-callout">Indexed {len(idx.doc_types_present)} document type(s). '
            f"Missing required: {_esc(', '.join(gaps))}</div>"
        )
    else:
        status = '<div class="pr-callout">All required document types present. Ready to review.</div>'
    return status, render_manifest(idx), idx


def ask(question, idx: PortfolioReviewIndex):
    if idx is None:
        return '<div class="pr-error">Build the index first (upload documents and click "Build index").</div>'
    if not question or not question.strip():
        return '<div class="pr-error">Enter a question, e.g. "Is Fund X suitable for this client?"</div>'
    try:
        review, _retrieved = idx.review(question)
    except Exception as e:
        return f'<div class="pr-error">Error while generating review: {_esc(str(e))}</div>'
    return render_review(review)


EXAMPLE_QUESTIONS = [
    "Is this fund suitable for the client given their risk profile?",
    "Explain in simple terms why this fund might not be a good fit for the client.",
    "Does this recommendation comply with our suitability policy?",
    "What would this client pay in fees, and is that reasonable given the fund's risk level?",
]

# This design has no dark-mode variant. Without this, Gradio auto-detects the
# browser/OS dark-mode preference and applies its own dark styling, which wins
# the CSS specificity fight against several of the custom colors above (cards
# render dark navy instead of white, text goes low-contrast). Forcing the
# `__theme=light` query param on load sidesteps that instead of overriding
# every dark-mode selector individually.
FORCE_LIGHT_JS = """
() => {
    const url = new URL(window.location);
    if (url.searchParams.get('__theme') !== 'light') {
        url.searchParams.set('__theme', 'light');
        window.location.href = url.href;
    }
}
"""

with gr.Blocks(title="Portfolio Review Copilot") as demo:
    gr.HTML(
        '<div class="pr-hero">'
        '<div class="pr-eyebrow">Advisory Compliance Tool</div>'
        '<h1 class="pr-title">Portfolio Review Copilot</h1>'
        '<p class="pr-subtitle">Upload factsheets, risk disclosures, suitability policy, '
        "client risk profile, fee disclosures, objective statements, or advisory notes, "
        "then ask whether a product or portfolio aligns with the client's profile. "
        "Answers are grounded only in the documents you upload.</p>"
        "</div>"
    )

    index_state = gr.State(None)

    with gr.Row():
        with gr.Column(scale=1):
            with gr.Group(elem_classes=["pr-card"]):
                gr.HTML('<div class="pr-panel-label">Case file</div>')
                file_input = gr.File(
                    label="Upload documents",
                    file_count="multiple",
                    file_types=[".pdf", ".docx", ".csv", ".xlsx", ".txt"],
                )
                build_btn = gr.Button("Build index", variant="primary")
                build_status = gr.HTML()

            with gr.Group(elem_classes=["pr-card"]):
                manifest_panel = gr.HTML(render_manifest(None))

        with gr.Column(scale=2):
            with gr.Group(elem_classes=["pr-card"]):
                gr.HTML('<div class="pr-panel-label">Ask the copilot</div>')
                with gr.Column():
                    question_input = gr.Textbox(
                        label=None,
                        placeholder="Is this fund suitable for the client given their risk profile?",
                        lines=2,
                        container=False,
                    )
                    gr.Examples(examples=EXAMPLE_QUESTIONS, inputs=question_input, label="Try one of these")
                    ask_btn = gr.Button("Review suitability", variant="primary")

            with gr.Group(elem_classes=["pr-card"]):
                gr.HTML('<div class="pr-panel-label">Review</div>')
                review_output = gr.HTML(
                    '<div class="pr-placeholder">Build the index, then ask a question to see the verdict.</div>'
                )

    build_btn.click(
        fn=build_index, inputs=[file_input], outputs=[build_status, manifest_panel, index_state]
    )
    ask_btn.click(fn=ask, inputs=[question_input, index_state], outputs=[review_output])

    demo.load(None, None, None, js=FORCE_LIGHT_JS)

def launch_app():
    demo.launch(css=CUSTOM_CSS, theme=gr.themes.Soft())


if __name__ == "__main__":
    launch_app()
