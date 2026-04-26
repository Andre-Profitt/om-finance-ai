"""Global stylesheet injected into every Streamlit page.

Restrained finance-grade palette. No emoji. No gradient. No rainbow tags.
Spacing is generous. Typography is the system stack — same as what the
Workday / Salesforce-class apps render.
"""

from __future__ import annotations

import streamlit as st

CSS = """
<style>
:root {
    --color-bg: #ffffff;
    --color-surface: #f6f7f9;
    --color-border: #e5e7eb;
    --color-border-strong: #d1d5db;
    --color-text: #111827;
    --color-text-muted: #6b7280;
    --color-text-faint: #9ca3af;
    --color-primary: #1e3a5f;
    --color-primary-soft: #eaf0f8;
    --color-success: #047857;
    --color-success-soft: #ecfdf5;
    --color-warning: #b45309;
    --color-warning-soft: #fffbeb;
    --color-danger: #b91c1c;
    --color-danger-soft: #fef2f2;
    --color-info: #1d4ed8;
    --color-info-soft: #eff6ff;
}

html, body, [class*="css"], [data-testid="stAppViewContainer"], [data-testid="stMarkdownContainer"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    color: var(--color-text);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

[data-testid="stAppViewContainer"] > .main {
    padding-top: 2rem;
    padding-bottom: 4rem;
    max-width: 1320px;
}

/* Hide default Streamlit chrome we don't want */
#MainMenu { visibility: hidden; }
header [data-testid="stToolbar"] { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] {
    background: transparent;
    height: 0;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--color-surface);
    border-right: 1px solid var(--color-border);
}
section[data-testid="stSidebar"] .stButton > button {
    width: 100%;
}

/* Page header band */
.page-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: 1rem;
    margin-bottom: 1.5rem;
}
.page-header h1 {
    font-size: 1.5rem;
    font-weight: 600;
    margin: 0 0 0.25rem 0;
    letter-spacing: -0.01em;
    color: var(--color-text);
}
.page-header .subtitle {
    font-size: 0.875rem;
    color: var(--color-text-muted);
    margin: 0;
}
.page-header .meta {
    font-size: 0.75rem;
    color: var(--color-text-faint);
    text-align: right;
    line-height: 1.5;
}
.page-header .meta code {
    background: var(--color-surface);
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    font-size: 0.7rem;
}

/* KPI cards */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 0.75rem;
    margin-bottom: 1.5rem;
}
.kpi-card {
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    padding: 1rem 1.25rem;
}
.kpi-card .label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--color-text-muted);
    font-weight: 500;
    margin-bottom: 0.4rem;
}
.kpi-card .value {
    font-size: 1.625rem;
    font-weight: 600;
    color: var(--color-text);
    line-height: 1.1;
    letter-spacing: -0.01em;
    font-variant-numeric: tabular-nums;
}
.kpi-card .footnote {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    margin-top: 0.4rem;
}
.kpi-card.accent { border-left: 3px solid var(--color-primary); }

/* Spark KPI: same outer styling but houses an altair chart underneath */
.kpi-spark {
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    padding: 1rem 1.25rem 0.5rem 1.25rem;
}
.kpi-spark .label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--color-text-muted);
    font-weight: 500;
    margin-bottom: 0.4rem;
}
.kpi-spark .value {
    font-size: 1.625rem;
    font-weight: 600;
    color: var(--color-text);
    line-height: 1.1;
    letter-spacing: -0.01em;
    font-variant-numeric: tabular-nums;
    margin-bottom: 0.4rem;
}
.kpi-spark .footnote {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    margin-top: 0.25rem;
}

/* Presenter mode — hides sidebar, centers main content for Loom screens */
body.presenter section[data-testid="stSidebar"] { display: none; }
body.presenter [data-testid="stAppViewContainer"] > .main {
    max-width: 1200px;
    margin: 0 auto;
}
body.presenter .page-header {
    border-bottom-width: 2px;
}

/* Status pills */
.pill {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.02em;
    line-height: 1.4;
    border: 1px solid transparent;
}
.pill.explained { color: var(--color-success); background: var(--color-success-soft); border-color: #a7f3d0; }
.pill.abstained { color: var(--color-warning); background: var(--color-warning-soft); border-color: #fde68a; }
.pill.high { color: var(--color-danger); background: var(--color-danger-soft); border-color: #fecaca; }
.pill.medium { color: var(--color-warning); background: var(--color-warning-soft); border-color: #fde68a; }
.pill.low { color: var(--color-text-muted); background: var(--color-surface); border-color: var(--color-border); }
.pill.info { color: var(--color-info); background: var(--color-info-soft); border-color: #c7d2fe; }
.pill.specialty {
    color: var(--color-primary);
    background: var(--color-primary-soft);
    border-color: #c7d8eb;
    text-transform: capitalize;
}

/* Citation card */
.citation-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 6px;
    padding: 1rem 1.25rem;
    margin: 0.75rem 0 0 0;
}
.citation-card .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}
.citation-card .doc {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    font-weight: 500;
    letter-spacing: 0.02em;
}
.citation-card .doc strong {
    color: var(--color-text);
    font-weight: 600;
}
.citation-card .similarity {
    font-size: 0.7rem;
    color: var(--color-text-faint);
    font-variant-numeric: tabular-nums;
}
.citation-card blockquote {
    margin: 0;
    padding-left: 0.75rem;
    border-left: 2px solid var(--color-primary);
    color: var(--color-text);
    font-size: 0.875rem;
    line-height: 1.55;
}

/* Section heading */
.section-h {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-text-muted);
    font-weight: 600;
    margin: 1.75rem 0 0.5rem 0;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: 0.4rem;
}

/* Dataframes — tighten + tabular numerics */
[data-testid="stDataFrame"] {
    border: 1px solid var(--color-border);
    border-radius: 6px;
    overflow: hidden;
}
[data-testid="stDataFrame"] table {
    font-variant-numeric: tabular-nums;
    font-size: 0.85rem;
}

/* Buttons — flatter, more deliberate */
.stButton > button {
    border-radius: 4px;
    border: 1px solid var(--color-border-strong);
    background: var(--color-bg);
    color: var(--color-text);
    font-weight: 500;
    font-size: 0.85rem;
    padding: 0.4rem 1rem;
    transition: background 80ms ease, border-color 80ms ease;
}
.stButton > button:hover {
    background: var(--color-surface);
    border-color: var(--color-primary);
    color: var(--color-primary);
}
.stButton > button[kind="primary"], .stButton button:focus {
    background: var(--color-primary);
    border-color: var(--color-primary);
    color: #ffffff;
}

/* Selectbox + multiselect — restrained */
[data-baseweb="select"] {
    font-size: 0.85rem;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid var(--color-border);
}
.stTabs [data-baseweb="tab"] {
    padding: 0.5rem 1rem;
    color: var(--color-text-muted);
    font-weight: 500;
    font-size: 0.875rem;
}
.stTabs [aria-selected="true"] {
    color: var(--color-primary);
    border-bottom: 2px solid var(--color-primary);
}

/* Footer */
.app-footer {
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid var(--color-border);
    color: var(--color-text-faint);
    font-size: 0.75rem;
    display: flex;
    justify-content: space-between;
}
.app-footer code {
    background: var(--color-surface);
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    font-size: 0.7rem;
}

/* Release-gate table */
.release-gate-table {
    border: 1px solid var(--color-border);
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 1.5rem;
    background: var(--color-bg);
}
.release-gate-row {
    display: grid;
    grid-template-columns: 1.4fr 0.6fr 2fr;
    gap: 1rem;
    padding: 0.6rem 1rem;
    align-items: center;
    border-bottom: 1px solid var(--color-border);
    font-size: 0.85rem;
}
.release-gate-row:last-child { border-bottom: none; }
.release-gate-head {
    background: var(--color-surface);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-text-muted);
    font-weight: 600;
}
.release-gate-row > div:nth-child(3) {
    color: var(--color-text-muted);
    font-size: 0.8rem;
}

/* Audit-event preview list */
.audit-event-list {
    display: grid;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
}
.audit-event-card {
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-left: 3px solid var(--color-primary);
    border-radius: 4px;
    padding: 0.6rem 0.9rem;
    font-size: 0.8rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.audit-event-row {
    display: grid;
    grid-template-columns: 180px 1fr;
    gap: 0.5rem;
    line-height: 1.5;
}
.audit-event-key {
    color: var(--color-text-muted);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.audit-event-val {
    color: var(--color-text);
    word-break: break-all;
}

/* Utility */
.hint {
    font-size: 0.8rem;
    color: var(--color-text-muted);
    margin-top: 0.25rem;
}
.kbd {
    background: var(--color-surface);
    border: 1px solid var(--color-border-strong);
    border-radius: 3px;
    padding: 0.05rem 0.3rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.75rem;
    color: var(--color-text-muted);
}
</style>
"""


PRESENTER_JS = """
<script>
(function() {
    try {
        const params = new URLSearchParams(window.parent.location.search);
        const on = params.get("presenter") === "1";
        const body = window.parent.document.body;
        if (on) body.classList.add("presenter");
        else body.classList.remove("presenter");
    } catch (e) { /* sandboxed iframe — ignore */ }
})();
</script>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def maybe_presenter_mode() -> bool:
    """Toggle presenter mode via ?presenter=1 query param.

    Hides the sidebar and centers the main content for clean Loom captures.
    """
    try:
        on = st.query_params.get("presenter") == "1"
    except Exception:
        on = False
    if on:
        st.markdown(
            "<style>section[data-testid='stSidebar']{display:none;} "
            "[data-testid='stAppViewContainer'] > .main{max-width:1200px;margin:0 auto;}</style>",
            unsafe_allow_html=True,
        )
    return on
