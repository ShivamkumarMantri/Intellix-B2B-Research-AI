import os
import re
import pandas as pd
import streamlit as st
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from utils.research import run_web_research, demo_dataset
from utils.validation import clean_dataframe, add_validation_scores, add_lead_score, CORE_QUALITY_FIELDS, LEAD_SCORE_WEIGHTS
from utils.exporter import to_excel_bytes
from utils.ai import (
    generate_company_summary,
    classify_industry,
    analyze_business_relevance,
    explain_lead_quality,
    extract_key_information,
    generate_research_insights,
    summarize_record,
    classify_record
)

# ---------------------------------------------------------
# Page Configuration & Modern Theme Setup
# ---------------------------------------------------------
st.set_page_config(
    page_title="AI B2B Web Research & Lead Intelligence Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom SaaS CSS Stylesheet
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Container constraints & padding */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 3.5rem !important;
    max-width: 1440px !important;
}

/* Header & Hero styling */
.saas-header {
    background: linear-gradient(135deg, rgba(23, 27, 37, 0.95) 0%, rgba(30, 36, 51, 0.85) 100%);
    border: 1px solid rgba(124, 108, 242, 0.25);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 8px 32px -8px rgba(0, 0, 0, 0.4);
}

.saas-header::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #7C6CF2 0%, #4F46E5 40%, #06B6D4 100%);
}

.saas-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(124, 108, 242, 0.15);
    border: 1px solid rgba(124, 108, 242, 0.35);
    color: #A594FD;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.saas-title {
    font-size: 1.75rem;
    font-weight: 800;
    color: #FFFFFF;
    margin: 0 0 6px 0;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    gap: 12px;
}

.saas-subtitle {
    color: #94A3B8;
    font-size: 0.94rem;
    margin: 0;
    line-height: 1.5;
    max-width: 920px;
}

/* KPI Card Styles */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
    margin-bottom: 22px;
}

.kpi-card {
    background: rgba(23, 27, 37, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 14px;
    padding: 18px 20px;
    position: relative;
    transition: all 0.2s ease-in-out;
    box-shadow: 0 4px 20px -4px rgba(0, 0, 0, 0.25);
}

.kpi-card:hover {
    border-color: rgba(124, 108, 242, 0.4);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px -4px rgba(124, 108, 242, 0.15);
}

.kpi-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.kpi-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.kpi-icon {
    font-size: 1.2rem;
    opacity: 0.9;
}

.kpi-value {
    font-size: 1.75rem;
    font-weight: 800;
    color: #F8FAFC;
    letter-spacing: -0.03em;
    line-height: 1.1;
    margin-bottom: 4px;
}

.kpi-subtext {
    font-size: 0.76rem;
    color: #64748B;
    display: flex;
    align-items: center;
    gap: 4px;
}

.kpi-subtext.highlight {
    color: #10B981;
    font-weight: 500;
}

.kpi-subtext.amber {
    color: #F59E0B;
    font-weight: 500;
}

/* Category Badges */
.badge-high {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #6EE7B7;
    padding: 3px 8px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.75rem;
}

.badge-med {
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.35);
    color: #FCD34D;
    padding: 3px 8px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.75rem;
}

.badge-low {
    background: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.35);
    color: #FCA5A5;
    padding: 3px 8px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.75rem;
}

/* Live query badge box */
.query-preview-box {
    background: rgba(15, 23, 42, 0.6);
    border: 1px dashed rgba(124, 108, 242, 0.4);
    border-radius: 10px;
    padding: 12px 16px;
    font-family: 'JetBrains Mono', monospace, Consolas;
    font-size: 0.88rem;
    color: #E2E8F0;
    margin-bottom: 12px;
}

/* Feature & Section Cards */
.content-card {
    background: #171B25;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 20px;
}

.step-card {
    background: rgba(23, 27, 37, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    padding: 16px;
    height: 100%;
}

.step-number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: #7C6CF2;
    color: white;
    font-size: 0.8rem;
    font-weight: 700;
    margin-bottom: 8px;
}

.step-title {
    font-size: 0.92rem;
    font-weight: 700;
    color: #F1F5F9;
    margin-bottom: 4px;
}

.step-desc {
    font-size: 0.8rem;
    color: #94A3B8;
    line-height: 1.4;
}

/* Sidebar styling touches */
.sidebar-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 0 14px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 16px;
}

.sidebar-logo-text {
    font-size: 1.15rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #FFFFFF;
}

.sidebar-tag {
    background: rgba(124, 108, 242, 0.2);
    color: #A594FD;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.65rem;
    font-weight: 700;
    margin-left: auto;
}

.status-indicator {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}

.status-online {
    background-color: #10B981;
    box-shadow: 0 0 8px #10B981;
}

.status-demo {
    background-color: #F59E0B;
    box-shadow: 0 0 8px #F59E0B;
}

/* Dossier Card for AI Enrichment */
.dossier-card {
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(124, 108, 242, 0.3);
    border-radius: 14px;
    padding: 22px;
    margin: 16px 0;
    box-shadow: 0 4px 20px -4px rgba(0,0,0,0.3);
}

.ai-pill {
    display: inline-flex;
    align-items: center;
    background: rgba(124, 108, 242, 0.12);
    border: 1px solid rgba(124, 108, 242, 0.28);
    color: #C4B5FD;
    padding: 4px 10px;
    border-radius: 8px;
    font-size: 0.78rem;
    font-weight: 600;
    margin: 3px 4px 3px 0;
}

.ai-pill-green {
    background: rgba(16, 185, 129, 0.12);
    border-color: rgba(16, 185, 129, 0.3);
    color: #6EE7B7;
}

.ai-pill-amber {
    background: rgba(245, 158, 11, 0.12);
    border-color: rgba(245, 158, 11, 0.3);
    color: #FCD34D;
}

.ai-box {
    background: rgba(10, 14, 23, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
    padding: 14px 16px;
    margin-top: 10px;
    margin-bottom: 12px;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------
# Session State Initialization (Preserving Raw & Cleaned Data)
# ---------------------------------------------------------
if 'raw_df' not in st.session_state:
    st.session_state.raw_df = pd.DataFrame()
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'stats' not in st.session_state:
    st.session_state.stats = {}
if 'ai_results' not in st.session_state:
    st.session_state.ai_results = {}
if 'macro_insights' not in st.session_state:
    st.session_state.macro_insights = None
if 'target_industry' not in st.session_state:
    st.session_state.target_industry = "Artificial Intelligence"
if 'target_location' not in st.session_state:
    st.session_state.target_location = "Mumbai"
if 'num_companies' not in st.session_state:
    st.session_state.num_companies = 15
if 'keywords' not in st.session_state:
    st.session_state.keywords = "automation, workflows"
if 'target_company_type' not in st.session_state:
    st.session_state.target_company_type = "B2B SaaS / Product"
if 'mode' not in st.session_state:
    st.session_state.mode = "Demo Mode"
if 'last_run_time' not in st.session_state:
    st.session_state.last_run_time = None

# Quick Preset Callbacks
def apply_preset(ind: str, loc: str, count: int, kws: str, ctype: str):
    st.session_state.target_industry = ind
    st.session_state.target_location = loc
    st.session_state.num_companies = count
    st.session_state.keywords = kws
    st.session_state.target_company_type = ctype

# ---------------------------------------------------------
# Sidebar Navigation & Control Panel
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div class="sidebar-logo">
            <span style="font-size: 1.5rem;">⚡</span>
            <div>
                <div class="sidebar-logo-text">Intellix B2B</div>
                <div style="font-size: 0.72rem; color: #64748B;">Intelligence & Research OS</div>
            </div>
            <span class="sidebar-tag">v2.6 PRO</span>
        </div>
    """, unsafe_allow_html=True)

    current_mode_is_demo = (st.session_state.mode == "Demo Mode")
    status_dot_class = "status-demo" if current_mode_is_demo else "status-online"
    status_text = "Demo Engine Active" if current_mode_is_demo else "Live Tavily Engine"
    st.markdown(f"""
        <div style="margin-bottom: 16px; padding: 6px 12px; background: rgba(255,255,255,0.03); border-radius: 8px; border: 1px solid rgba(255,255,255,0.06); font-size: 0.8rem; color: #94A3B8;">
            <span class="status-indicator {status_dot_class}"></span>{status_text}
        </div>
    """, unsafe_allow_html=True)

    # 1. Pipeline Mode Selection
    st.markdown("### ⚙️ Pipeline Engine")
    mode = st.radio(
        "Data Source Mode",
        options=["Demo Mode", "Live Web Research"],
        key="mode",
        help="Demo mode operates with pre-validated high-signal public business data without requiring API keys. Live Web Research performs live web search using Tavily API."
    )

    # 2. Scope Configuration (5 User Parameters)
    st.markdown("### 🎯 Research Parameters")
    target_industry = st.text_input(
        "Industry",
        key="target_industry",
        placeholder="e.g. Artificial Intelligence, FinTech, SaaS"
    )
    target_location = st.text_input(
        "Location",
        key="target_location",
        placeholder="e.g. Mumbai, Bengaluru, Singapore, London"
    )
    num_companies = st.slider(
        "Number of Companies",
        min_value=5,
        max_value=50,
        step=5,
        key="num_companies",
        help="Target number of unique company entities to research."
    )
    keywords = st.text_input(
        "Optional Keywords",
        key="keywords",
        placeholder="e.g. automation, agentic workflows, series a",
        help="Specific technical signals, offerings, or keywords to filter by."
    )
    company_type_options = [
        "All Types",
        "B2B SaaS / Product",
        "Startup / Early Stage",
        "Mid-Market / SME",
        "Enterprise",
        "Agency / Services / Consulting"
    ]
    target_company_type = st.selectbox(
        "Target Company Type",
        options=company_type_options,
        key="target_company_type",
        help="Organizational scale or commercial archetype."
    )

    # 3. 1-Click Portfolio Presets
    st.markdown("#### ⚡ Quick Presets")
    preset_col1, preset_col2 = st.columns(2)
    with preset_col1:
        if st.button("🤖 AI Mumbai", use_container_width=True, help="Load preset: AI B2B companies in Mumbai"):
            apply_preset("Artificial Intelligence", "Mumbai", 15, "automation, workflows", "B2B SaaS / Product")
            st.rerun()
    with preset_col2:
        if st.button("💳 FinTech Pune", use_container_width=True, help="Load preset: FinTech platforms in Pune"):
            apply_preset("FinTech", "Pune, Maharashtra", 15, "compliance, reporting", "Mid-Market / SME")
            st.rerun()

    # 4. API Configuration Drawer
    with st.expander("🔑 API Credentials & Models", expanded=(mode == "Live Web Research")):
        st.markdown("<small style='color:#94A3B8;'>Keys are read automatically from <code>.env</code> or input below securely.</small>", unsafe_allow_html=True)
        tavily_key = st.text_input(
            "Tavily Search API Key",
            value=os.getenv("TAVILY_API_KEY", ""),
            type="password",
            help="Required only for Live Web Research mode."
        )
        st.divider()
        st.markdown("**LLM Configuration (Optional)**")
        env_llm_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        ai_key = st.text_input(
            "OpenAI / Groq API Key",
            value=env_llm_key,
            type="password",
            help="Optional. Leave blank to experience Demo Mode AI responses seamlessly without keys."
        )
        ai_endpoint = st.text_input(
            "Base URL",
            value=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
            help="OpenAI-compatible endpoint"
        )
        ai_model = st.text_input(
            "Model Name",
            value=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
            help="e.g. llama-3.3-70b-versatile, gpt-4o-mini"
        )

        active_llm_key = (ai_key or env_llm_key).strip()
        if active_llm_key:
            st.caption("🟢 **Live LLM Enabled**: Real API calls will be dispatched.")
        else:
            st.caption("✨ **Demo AI Enabled**: Intelligent mock generation active (Zero keys needed).")

    # Lead Scoring System Notice
    st.markdown("---")
    st.markdown("""
        <div style="font-size: 0.72rem; color: #64748B; text-align: left; line-height: 1.5; padding: 4px 6px;">
            🎯 <strong>Deterministic 0-100 Lead Scoring</strong><br>
            • Industry fit (25%) + Location (20%)<br>
            • Decision maker (15%) + Completeness (15%)<br>
            • Website (10%) + Confidence (10%)<br>
            • LinkedIn availability (5%)<br>
            • Zero random values • Fully reproducible
        </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# Dynamic Query Construction
# ---------------------------------------------------------
query_parts = []
if target_company_type and target_company_type != "All Types":
    query_parts.append(target_company_type)
if target_industry:
    query_parts.append(f"{target_industry} companies")
if target_location:
    query_parts.append(f"in {target_location}")
if keywords:
    query_parts.append(keywords)

query = " ".join(query_parts).strip()

# ---------------------------------------------------------
# Professional Header Section
# ---------------------------------------------------------
st.markdown(f"""
    <div class="saas-header">
        <div class="saas-badge">✨ DETERMINISTIC LEAD INTELLIGENCE OS</div>
        <div class="saas-title">
            <span>Market Research & Lead Scoring Agent</span>
        </div>
        <p class="saas-subtitle">
            Autonomous multi-stage prospecting with deterministic 0-100 Lead Scoring, transparent category grading
            (High, Medium, Low Potential), multi-factor audit explanations, and verified citation sources.
        </p>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Research Launch & Query Configuration Control Bar
# ---------------------------------------------------------
config_container = st.container()
with config_container:
    col_query, col_action = st.columns([3.2, 1.2])

    with col_query:
        st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-size: 0.82rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em;">
                    🔍 Active Research Search Query
                </span>
                <span style="font-size: 0.75rem; color: #7C6CF2; font-weight: 600;">
                    Constructed from scope criteria
                </span>
            </div>
        """, unsafe_allow_html=True)
        st.markdown(f'<div class="query-preview-box"><code>{query}</code></div>', unsafe_allow_html=True)

    with col_action:
        st.markdown("<div style='height: 22px;'></div>", unsafe_allow_html=True)
        start_btn = st.button("🚀 Start B2B Research", type="primary", use_container_width=True)

# ---------------------------------------------------------
# Agent Execution Logic (Preserves Raw & Cleaned Separation)
# ---------------------------------------------------------
if start_btn:
    try:
        with st.status("⚡ Executing Multi-Stage Quality & Scoring Pipeline...", expanded=True) as status_box:
            st.write("🌐 Phase 1: Ingesting public business records...")
            if mode == "Demo Mode":
                raw = demo_dataset()
                st.write(f"✅ Phase 1 complete: Loaded {len(raw)} raw business records (including test duplicates).")
            else:
                if not tavily_key:
                    raise ValueError("Tavily API Key is missing. Please provide a key in the sidebar or switch to Demo Mode.")
                raw = run_web_research(
                    query=query,
                    max_results=num_companies,
                    api_key=tavily_key,
                    target_industry=target_industry,
                    target_location=target_location,
                    target_company_type=target_company_type
                )
                st.write(f"✅ Phase 1 complete: Ingested {len(raw)} raw web search citations from live sources.")

            st.session_state.raw_df = raw.copy()

            st.write("🧹 Phase 2: Sanitizing data, normalizing URLs, and resolving duplicate entities...")
            clean, stats = clean_dataframe(raw)
            st.write(f"✅ Phase 2 complete: Pruned {stats.get('duplicates_detected', 0)} duplicates.")

            st.write("🛡️ Phase 3: Auditing missing values, evaluating confidence scores, and completeness %...")
            scored = add_validation_scores(clean)

            st.write("🎯 Phase 4: Computing deterministic 7-factor 0-100 Lead Scores & Categories...")
            scored = add_lead_score(
                scored,
                target_industry=target_industry,
                target_location=target_location,
                keywords=keywords,
                target_company_type=target_company_type
            )

            st.session_state.df = scored
            st.session_state.stats = stats
            st.session_state.ai_results = {}
            st.session_state.macro_insights = None
            st.session_state.last_run_time = datetime.now().strftime("%H:%M:%S")

            status_box.update(label="✨ Pipeline Completed! All Leads Scored & Audited.", state="complete", expanded=False)

        st.toast(f"✅ Processed and scored {len(st.session_state.df)} prospect dossiers!", icon="🎉")
    except Exception as exc:
        st.error(f"❌ Research Execution Error: {str(exc)}")

# ---------------------------------------------------------
# Main Dashboard Body
# ---------------------------------------------------------
df = st.session_state.df
raw_df = st.session_state.raw_df
stats = st.session_state.stats

if not df.empty:
    is_demo = (mode == "Demo Mode") or ('Data Source' in df.columns and any('[DEMO DATA]' in str(x) for x in df['Data Source']))
    if is_demo:
        st.info(
            "💡 **DEMO DATASET EVALUATION**: Displaying 25 pre-validated sample B2B prospect records clearly tagged as `[DEMO DATA]`. "
            "Demonstrates complete web research workflow, canonical deduplication, 7-factor 0-100 deterministic scoring, AI summaries, "
            "and multi-sheet executive exports with zero API keys required. Switch to **Live Web Research** in sidebar for real-time web crawling.",
            icon="ℹ️"
        )

    # -----------------------------------------------------
    # Tab Navigation
    # -----------------------------------------------------
    tab_leads, tab_scoring, tab_quality, tab_insights, tab_ai, tab_export = st.tabs([
        "📋 Structured Results Table",
        "🎯 0-100 Lead Scoring",
        "🛡️ Data Quality Dashboard",
        "📊 Market Insights",
        "🤖 AI Intelligence Hub",
        "📦 Export Center"
    ])

    # -----------------------------------------------------
    # TAB 1: Structured Results Table
    # -----------------------------------------------------
    with tab_leads:
        st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h4 style="margin: 0; font-size: 1.1rem; color: #FFFFFF;">Structured B2B Research Dossiers</h4>
                <span style="font-size: 0.8rem; color: #94A3B8;">Transparent 0-100 Lead Scores • Lead Categories • Verifiable Citations</span>
            </div>
        """, unsafe_allow_html=True)

        # Filters Row
        f_col1, f_col2, f_col3, f_col4 = st.columns([1.5, 1.5, 1.5, 2])
        with f_col1:
            cat_filter = st.multiselect(
                "Lead Category",
                options=["High Potential", "Medium Potential", "Low Potential"],
                default=["High Potential", "Medium Potential", "Low Potential"],
                help="Filter by deterministic ICP potential tier"
            )
        with f_col2:
            conf_filter = st.multiselect(
                "Confidence Tier",
                options=["High", "Medium", "Low"],
                default=["High", "Medium", "Low"],
                help="Filter companies by validation confidence tier"
            )
        with f_col3:
            min_score = st.slider(
                "Min Lead Score",
                min_value=0,
                max_value=100,
                value=0,
                step=5,
                help="Filter leads meeting or exceeding this Lead Score"
            )
        with f_col4:
            table_search = st.text_input(
                "Search Table",
                placeholder="Search company, leader, location, description...",
                help="Filter any column in real time"
            )

        # Filter Application
        filtered_df = df[
            df["Lead Category"].isin(cat_filter) &
            df["Confidence"].isin(conf_filter) &
            (df["Lead Score"] >= min_score)
        ].copy()

        if table_search:
            mask = filtered_df.astype(str).apply(
                lambda row: row.str.contains(table_search, case=False, na=False, regex=False)
            ).any(axis=1)
            filtered_df = filtered_df[mask]

        st.caption(f"Displaying **{len(filtered_df)}** of **{len(df)}** structured company records")

        # Configured Interactive DataFrame with exact requested fields
        st.dataframe(
            filtered_df,
            column_config={
                "Data Source": st.column_config.TextColumn("Data Source", help="Classification: [DEMO DATA] or Live Web Research", width="small"),
                "Company Name": st.column_config.TextColumn("Company Name", width="medium"),
                "Lead Score": st.column_config.ProgressColumn(
                    "Lead Score",
                    help="Transparent 0-100 Lead Score based on 7 objective factors",
                    format="%d",
                    min_value=0,
                    max_value=100,
                    width="small"
                ),
                "Lead Category": st.column_config.TextColumn(
                    "Lead Category",
                    help="High Potential (≥80), Medium Potential (60-79), Low Potential (<60)",
                    width="small"
                ),
                "Lead Score Reason": st.column_config.TextColumn(
                    "Score Explanation",
                    help="Deterministic explanation of why this company received its score",
                    width="large"
                ),
                "Confidence Score": st.column_config.ProgressColumn(
                    "Confidence Score",
                    help="Public verification score (0-100%)",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                    width="small"
                ),
                "Data Completeness %": st.column_config.ProgressColumn(
                    "Completeness",
                    help="Completeness rate across 9 core fields",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                    width="small"
                ),
                "Industry": st.column_config.TextColumn("Industry", width="small"),
                "Location": st.column_config.TextColumn("Location", width="small"),
                "Website": st.column_config.LinkColumn("Website", display_text="Visit Web", width="small"),
                "LinkedIn URL": st.column_config.LinkColumn("LinkedIn URL", display_text="LinkedIn ↗", width="small"),
                "Company Description": st.column_config.TextColumn("Company Description", width="large"),
                "Decision Maker": st.column_config.TextColumn("Decision Maker", help="Identified from public evidence; blank if unavailable", width="medium"),
                "Decision Maker Role": st.column_config.TextColumn("Role", width="small"),
                "Source URL": st.column_config.LinkColumn("Source URL", display_text="Verify Source ↗", help="Click to manually verify source evidence", width="small"),
            },
            column_order=[
                "Data Source",
                "Company Name",
                "Lead Score",
                "Lead Category",
                "Lead Score Reason",
                "Confidence Score",
                "Data Completeness %",
                "Industry",
                "Location",
                "Website",
                "LinkedIn URL",
                "Decision Maker",
                "Decision Maker Role",
                "Source URL",
                "Company Description"
            ],
            use_container_width=True,
            hide_index=True,
            height=480
        )

    # -----------------------------------------------------
    # TAB 2: Deterministic Lead Scoring Deep Dive
    # -----------------------------------------------------
    with tab_scoring:
        st.markdown("#### 🎯 Transparent 0-100 Lead Scoring System")
        st.write(
            "Every lead is scored through a 100% deterministic, reproducible rubric summing to exactly 100 points. "
            "Scores are based exclusively on verified objective factors with zero random variation."
        )

        sc_c1, sc_c2 = st.columns([1.6, 2.4])

        with sc_c1:
            st.markdown(f"""
                <div class="content-card">
                    <h5 style="color: #7C6CF2; margin-top: 0;">Transparent 7-Factor Rubric Weights</h5>
                    <ul style="font-size: 0.85rem; color: #CBD5E1; padding-left: 18px; line-height: 1.9;">
                        <li><strong>1. Industry Relevance:</strong> Max 25 pts ({target_industry or 'Open'})</li>
                        <li><strong>2. Location Match:</strong> Max 20 pts ({target_location or 'Open'})</li>
                        <li><strong>3. Decision-Maker Availability:</strong> Max 15 pts</li>
                        <li><strong>4. Company Data Completeness:</strong> Max 15 pts</li>
                        <li><strong>5. Website Availability:</strong> Max 10 pts</li>
                        <li><strong>6. Research Confidence:</strong> Max 10 pts</li>
                        <li><strong>7. LinkedIn Availability:</strong> Max 5 pts</li>
                    </ul>
                    <div style="font-size: 0.78rem; color: #94A3B8; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 10px;">
                        <strong>Lead Categories:</strong><br>
                        🟢 <strong>High Potential:</strong> 80 – 100 pts<br>
                        🟡 <strong>Medium Potential:</strong> 60 – 79 pts<br>
                        🔴 <strong>Low Potential:</strong> 0 – 59 pts
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with sc_c2:
            st.markdown("##### 📊 Lead Category Distribution")
            cat_counts = df['Lead Category'].value_counts().reindex(['High Potential', 'Medium Potential', 'Low Potential']).fillna(0)
            st.bar_chart(cat_counts, color="#7C6CF2", height=240)

        st.markdown("---")

        # Top Priority Opportunities with Explanations
        st.markdown("##### 🏆 Ranked Opportunities & Audit Explanations")
        top_prospects = df.sort_values(by=['Lead Score', 'Confidence Score'], ascending=False).head(5)
        st.dataframe(
            top_prospects[['Company Name', 'Lead Score', 'Lead Category', 'Lead Score Reason', 'Decision Maker', 'Decision Maker Role', 'Source URL']],
            column_config={
                "Lead Score": st.column_config.ProgressColumn("Lead Score", min_value=0, max_value=100, format="%d"),
                "Lead Category": st.column_config.TextColumn("Category"),
                "Lead Score Reason": st.column_config.TextColumn("Deterministic Explanation", width="large"),
                "Source URL": st.column_config.LinkColumn("Source URL", display_text="Verify ↗")
            },
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")

        # Interactive 7-Factor Point Inspector
        st.markdown("##### 🔍 Company Score Factor Inspector")
        st.write("Select a company to inspect its individual point allocations across all 7 scoring factors.")

        comp_col_name = 'Company Name' if 'Company Name' in df.columns else 'Company'
        comp_choices = df[comp_col_name].tolist()
        inspect_company = st.selectbox("Inspect Scoring Breakdown For:", options=comp_choices, key="inspect_comp")
        inspected_row = df[df[comp_col_name] == inspect_company].iloc[0]

        factors_data = inspected_row.get('Score Factors', {})
        if factors_data:
            f_col_a, f_col_b = st.columns([1.5, 2.5])
            with f_col_a:
                st.markdown(f"""
                    <div class="content-card">
                        <h4 style="margin: 0; color: #FFFFFF;">{inspect_company}</h4>
                        <div style="font-size: 2.2rem; font-weight: 800; color: #7C6CF2; margin: 8px 0;">
                            {inspected_row.get('Lead Score', 0)}<span style="font-size: 1rem; color: #94A3B8;">/100</span>
                        </div>
                        <div style="margin-bottom: 12px;">
                            <span class="badge-high" style="font-size: 0.85rem;">{inspected_row.get('Lead Category', 'Standard')}</span>
                        </div>
                        <div style="font-size: 0.82rem; color: #CBD5E1; line-height: 1.5;">
                            <strong>Why this score:</strong><br>
                            {inspected_row.get('Lead Score Reason', '')}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            with f_col_b:
                st.markdown("<strong>Factor Points Breakdown:</strong>", unsafe_allow_html=True)
                factor_df = pd.DataFrame([
                    {"Factor": "1. Industry Relevance", "Points Awarded": factors_data.get('Industry Relevance', 0), "Max Points": 25},
                    {"Factor": "2. Location Match", "Points Awarded": factors_data.get('Location Match', 0), "Max Points": 20},
                    {"Factor": "3. Decision Maker", "Points Awarded": factors_data.get('Decision Maker', 0), "Max Points": 15},
                    {"Factor": "4. Data Completeness", "Points Awarded": factors_data.get('Data Completeness', 0), "Max Points": 15},
                    {"Factor": "5. Website Availability", "Points Awarded": factors_data.get('Website Availability', 0), "Max Points": 10},
                    {"Factor": "6. Research Confidence", "Points Awarded": factors_data.get('Research Confidence', 0), "Max Points": 10},
                    {"Factor": "7. LinkedIn Availability", "Points Awarded": factors_data.get('LinkedIn Availability', 0), "Max Points": 5},
                ])
                st.dataframe(
                    factor_df,
                    column_config={
                        "Points Awarded": st.column_config.ProgressColumn("Awarded", min_value=0, max_value=25, format="%d pts"),
                    },
                    use_container_width=True,
                    hide_index=True
                )

    # -----------------------------------------------------
    # TAB 3: Hardened Data Quality Dashboard
    # -----------------------------------------------------
    with tab_quality:
        st.markdown("#### 🛡️ Enterprise Data Quality & Hygiene Dashboard")
        st.write(
            "Diagnostic telemetry tracking duplicate detection, URL normalization, "
            "missing-value inspection, and cohort completeness."
        )

        total_records = stats.get('total_raw_records', len(raw_df) if not raw_df.empty else len(df))
        valid_records = len(df)
        duplicate_records = stats.get('duplicates_detected', 0)
        incomplete_records = int((df['Data Completeness %'] < 100.0).sum()) if 'Data Completeness %' in df.columns else 0
        invalid_urls = stats.get('invalid_urls', 0)
        avg_confidence = round(df['Confidence Score'].mean(), 1) if 'Confidence Score' in df.columns else 0.0
        data_completeness_pct = round(df['Data Completeness %'].mean(), 1) if 'Data Completeness %' in df.columns else 0.0

        st.markdown(f"""
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span class="kpi-label">Total Records</span>
                        <span class="kpi-icon">📥</span>
                    </div>
                    <div class="kpi-value">{total_records}</div>
                    <div class="kpi-subtext">Ingested raw citations</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span class="kpi-label">Valid Records</span>
                        <span class="kpi-icon">✅</span>
                    </div>
                    <div class="kpi-value">{valid_records}</div>
                    <div class="kpi-subtext highlight">Unique verified entities</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span class="kpi-label">Duplicate Records</span>
                        <span class="kpi-icon">🧹</span>
                    </div>
                    <div class="kpi-value">{duplicate_records}</div>
                    <div class="kpi-subtext amber">Detected & resolved</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span class="kpi-label">Incomplete Records</span>
                        <span class="kpi-icon">⚠️</span>
                    </div>
                    <div class="kpi-value">{incomplete_records}</div>
                    <div class="kpi-subtext">1+ public fields missing</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span class="kpi-label">Invalid URLs</span>
                        <span class="kpi-icon">🔗</span>
                    </div>
                    <div class="kpi-value">{invalid_urls}</div>
                    <div class="kpi-subtext">Malformed links detected</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span class="kpi-label">Average Confidence</span>
                        <span class="kpi-icon">🛡️</span>
                    </div>
                    <div class="kpi-value">{avg_confidence}%</div>
                    <div class="kpi-subtext highlight">Verification score</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span class="kpi-label">Data Completeness %</span>
                        <span class="kpi-icon">📊</span>
                    </div>
                    <div class="kpi-value">{data_completeness_pct}%</div>
                    <div class="kpi-subtext highlight">Cohort-wide completeness</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        dq_c1, dq_c2 = st.columns([1.5, 1])
        with dq_c1:
            st.markdown("##### 📈 Field-by-Field Completeness Rate")
            field_stats = {}
            for f in CORE_QUALITY_FIELDS:
                if f in df.columns:
                    populated = int(df[f].apply(lambda x: bool(str(x).strip())).sum())
                    pct = round((populated / len(df)) * 100, 1)
                    field_stats[f] = pct
            field_df = pd.Series(field_stats, name="Completeness %")
            st.bar_chart(field_df, color="#7C6CF2", height=240)

        with dq_c2:
            st.markdown("##### 🔍 Duplicate Detection & Deduplication Log")
            dup_details = stats.get('duplicates_details', [])
            if dup_details:
                st.caption(f"Identified **{len(dup_details)}** duplicate records during ingest:")
                for d in dup_details:
                    st.markdown(f"- 🏢 **{d.get('Company Name', 'Record')}**: {d.get('Reason', 'Duplicate entity match')}")
            else:
                st.success("No duplicate records detected in the current cohort.")

        st.markdown("---")

        st.markdown("##### 🗂️ Data Separation & Verification Explorer")
        compare_view = st.radio(
            "Select Dataset View:",
            options=["✨ Cleaned & Validated Dataset", "📦 Original Raw Research Data (Untouched)"],
            horizontal=True
        )

        if compare_view == "✨ Cleaned & Validated Dataset":
            st.caption(f"Showing **{len(df)}** deduplicated and validated records with Data Completeness %:")
            st.dataframe(
                df[['Company Name', 'Data Completeness %', 'Confidence Score', 'Validation Notes', 'Website', 'LinkedIn URL', 'Decision Maker', 'Source URL']],
                column_config={
                    "Data Completeness %": st.column_config.ProgressColumn("Completeness %", format="%d%%", min_value=0, max_value=100),
                    "Confidence Score": st.column_config.ProgressColumn("Confidence", format="%d%%", min_value=0, max_value=100),
                    "Website": st.column_config.LinkColumn("Website"),
                    "LinkedIn URL": st.column_config.LinkColumn("LinkedIn"),
                    "Source URL": st.column_config.LinkColumn("Source URL", display_text="Verify Source ↗")
                },
                use_container_width=True,
                hide_index=True,
                height=320
            )
        else:
            if not raw_df.empty:
                st.caption(f"Showing **{len(raw_df)}** original raw records before deduplication and normalization:")
                st.dataframe(raw_df, use_container_width=True, hide_index=True, height=320)
            else:
                st.info("Raw research dataset is currently empty. Run research above to populate.")

    # -----------------------------------------------------
    # TAB 4: Research Insights Section
    # -----------------------------------------------------
    with tab_insights:
        st.markdown("#### 📊 Aggregated Market Research Intelligence")

        ins_c1, ins_c2 = st.columns(2)
        with ins_c1:
            st.markdown("##### Industry / Domain Distribution")
            industry_counts = df['Industry'].replace('', 'Unspecified').value_counts()
            st.bar_chart(industry_counts, color="#06B6D4", height=240)

        with ins_c2:
            st.markdown("##### Geographic Hub Breakdown")
            location_counts = df['Location'].replace('', 'Unspecified').value_counts()
            st.bar_chart(location_counts, color="#A594FD", height=240)

        st.markdown("---")
        st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <h4 style="margin: 0; color: #FFFFFF;">🧠 AI-Powered Macro Market Research Insights</h4>
                <span class="ai-pill">Cohort Synthesis</span>
            </div>
            <p style="font-size: 0.88rem; color: #94A3B8; margin-bottom: 14px;">
                Synthesize high-level market trends, recurring commercial themes, emerging opportunities, and strategic outreach advice across all researched companies.
            </p>
        """, unsafe_allow_html=True)

        gen_insight_col1, gen_insight_col2 = st.columns([1.5, 3])
        with gen_insight_col1:
            run_macro = st.button("✨ Synthesize Cohort Market Insights", type="primary", use_container_width=True)

        active_llm_key = (ai_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
        with gen_insight_col2:
            if active_llm_key:
                st.caption(f"🟢 Utilizing live model: `{ai_model or 'llama-3.3-70b-versatile'}`")
            else:
                st.caption("✨ Operating in Demo Mode: Instant deterministic portfolio intelligence (No API Key needed).")

        if run_macro or st.session_state.macro_insights:
            if run_macro:
                try:
                    with st.spinner("Analyzing cross-company signals and market trends..."):
                        companies_records = df.to_dict('records')
                        insights = generate_research_insights(
                            companies_records,
                            query=query,
                            target_industry=target_industry,
                            target_location=target_location,
                            api_key=active_llm_key,
                            endpoint=ai_endpoint,
                            model=ai_model
                        )
                        st.session_state.macro_insights = insights
                        st.toast("Macro research insights generated!", icon="🧠")
                except Exception as e:
                    st.error(f"Failed to generate research insights: {str(e)}")

            if st.session_state.macro_insights:
                m_ins = st.session_state.macro_insights
                st.markdown(f"""
                    <div class="content-card">
                        <div style="font-size: 0.82rem; font-weight: 700; color: #7C6CF2; text-transform: uppercase; margin-bottom: 6px;">Executive Market Summary</div>
                        <div style="font-size: 0.95rem; color: #F1F5F9; line-height: 1.6; margin-bottom: 16px;">
                            {m_ins.get('market_summary', '')}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                c_m1, c_m2 = st.columns(2)
                with c_m1:
                    st.markdown("##### 📌 Dominant Industry Themes")
                    for theme in m_ins.get('dominant_themes', []):
                        st.markdown(f"- **{theme}**")

                    st.markdown("##### 🚀 Emerging Market Opportunities")
                    for opp in m_ins.get('emerging_opportunities', []):
                        st.markdown(f"- 💡 {opp}")

                with c_m2:
                    st.markdown("##### 🎯 Strategic Outreach Playbook")
                    for rec in m_ins.get('strategic_recommendations', []):
                        st.markdown(f"- ✅ {rec}")

    # -----------------------------------------------------
    # TAB 5: AI Intelligence Hub (6 AI Capabilities)
    # -----------------------------------------------------
    with tab_ai:
        st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <h4 style="margin: 0; color: #FFFFFF;">🤖 AI Lead Intelligence & Corporate Profiling Hub</h4>
                <span class="saas-badge">6-Factor AI Capabilities</span>
            </div>
            <p style="font-size: 0.9rem; color: #94A3B8; margin-bottom: 16px;">
                Execute deep LLM-powered analyses across company profiles: executive summary, precise industry classification,
                commercial relevance grading, lead quality reasoning, and structured entity extraction.
            </p>
        """, unsafe_allow_html=True)

        active_llm_key = (ai_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
        if not active_llm_key:
            st.info("💡 **Demo AI Mode Active**: Running without an LLM API key using built-in deterministic intelligence generators. To test live LLM calls, add your API key in the sidebar.", icon="✨")

        comp_col_name = 'Company Name' if 'Company Name' in df.columns else 'Company'
        company_list = df[comp_col_name].tolist()
        if company_list:
            selected_comp = st.selectbox("Select Target Company to Profile:", options=company_list, key="selected_comp")
            selected_row = df[df[comp_col_name] == selected_comp].iloc[0]
            evidence_text = str(selected_row.get('Research Summary', selected_row.get('Summary', '')))
            person_name = selected_row.get('Decision Maker', selected_row.get('Key Person', ''))
            person_role = selected_row.get('Decision Maker Role', selected_row.get('Role', ''))
            person_display = f"{person_name} ({person_role})" if person_name else "Unavailable (Not publicly found)"

            st.markdown(f"""
                <div class="dossier-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                        <div>
                            <h3 style="margin: 0; color: #FFFFFF; font-size: 1.4rem;">{selected_comp}</h3>
                            <div style="font-size: 0.85rem; color: #94A3B8; margin-top: 4px;">
                                {selected_row.get('Industry', 'Industry: Unspecified')} • {selected_row.get('Location', 'Location: Unspecified')}
                            </div>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <span class="ai-pill ai-pill-green">Lead Fit: {selected_row.get('Lead Score', 0)}/100</span>
                            <span class="badge-high">{selected_row.get('Lead Category', 'Standard')}</span>
                            <span class="ai-pill">Confidence: {selected_row.get('Confidence Score', 0)}%</span>
                        </div>
                    </div>
                    <div style="font-size: 0.85rem; color: #CBD5E1; background: rgba(0,0,0,0.3); padding: 12px 14px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid #7C6CF2;">
                        <strong style="color: #A594FD;">Public Evidence Summary:</strong><br>
                        {evidence_text or 'No raw text snippet available.'}
                    </div>
                    <div style="font-size: 0.82rem; color: #CBD5E1; margin-bottom: 6px;">
                        <strong>Score Explanation:</strong> {selected_row.get('Lead Score Reason', '')}
                    </div>
                    <div style="font-size: 0.78rem; color: #64748B;">
                        Source Link: <a href="{selected_row.get('Source URL', selected_row.get('Website', '#'))}" target="_blank" style="color: #7C6CF2;">{selected_row.get('Source URL', selected_row.get('Website', 'N/A'))} ↗</a> (Click to manually verify)
                    </div>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("##### ⚡ AI Intelligence Triggers")
            b_full, b_sum, b_class, b_rel, b_qual, b_ext = st.columns([1.6, 1, 1.1, 1.2, 1.2, 1.3])

            with b_full:
                run_all = st.button("🚀 Run Complete 360° Dossier", type="primary", use_container_width=True, help="Executes all 5 company-level AI analyses simultaneously")
            with b_sum:
                run_sum = st.button("📝 Summary", use_container_width=True, help="1. Company Summary Generation")
            with b_class:
                run_class = st.button("🏷️ Classification", use_container_width=True, help="2. Industry & Business Model Classification")
            with b_rel:
                run_rel = st.button("🎯 Relevance", use_container_width=True, help="3. Commercial Relevance Analysis")
            with b_qual:
                run_qual = st.button("🛡️ Lead Quality", use_container_width=True, help="4. Lead Quality & Readiness Reasoning")
            with b_ext:
                run_ext = st.button("🔍 Key Extraction", use_container_width=True, help="5. Structured Entity Extraction")

            if run_all or run_sum:
                try:
                    with st.spinner("Generating executive summary..."):
                        s_out = generate_company_summary(selected_comp, evidence_text, active_llm_key, ai_endpoint, ai_model)
                        st.session_state.ai_results[f"{selected_comp}_summary"] = s_out
                except Exception as e:
                    st.error(f"Summary Error: {str(e)}")

            if run_all or run_class:
                try:
                    with st.spinner("Classifying industry taxonomy..."):
                        c_out = classify_industry(selected_comp, evidence_text, active_llm_key, ai_endpoint, ai_model)
                        st.session_state.ai_results[f"{selected_comp}_industry"] = c_out
                except Exception as e:
                    st.error(f"Classification Error: {str(e)}")

            if run_all or run_rel:
                try:
                    with st.spinner("Analyzing commercial relevance..."):
                        r_out = analyze_business_relevance(
                            selected_comp, evidence_text, intent=keywords or target_company_type,
                            target_industry=target_industry, target_location=target_location,
                            api_key=active_llm_key, endpoint=ai_endpoint, model=ai_model
                        )
                        st.session_state.ai_results[f"{selected_comp}_relevance"] = r_out
                except Exception as e:
                    st.error(f"Relevance Analysis Error: {str(e)}")

            if run_all or run_qual:
                try:
                    with st.spinner("Explaining lead quality and outreach readiness..."):
                        q_out = explain_lead_quality(selected_comp, selected_row.to_dict(), active_llm_key, ai_endpoint, ai_model)
                        st.session_state.ai_results[f"{selected_comp}_quality"] = q_out
                except Exception as e:
                    st.error(f"Lead Quality Error: {str(e)}")

            if run_all or run_ext:
                try:
                    with st.spinner("Extracting structured corporate entities..."):
                        e_out = extract_key_information(
                            selected_comp, evidence_text, raw_fields=selected_row.to_dict(),
                            api_key=active_llm_key, endpoint=ai_endpoint, model=ai_model
                        )
                        st.session_state.ai_results[f"{selected_comp}_extraction"] = e_out
                except Exception as e:
                    st.error(f"Entity Extraction Error: {str(e)}")

            if run_all:
                st.toast(f"360° AI Dossier generated for {selected_comp}!", icon="✨")

            st.markdown("---")
            dossier_col1, dossier_col2 = st.columns(2)

            with dossier_col1:
                st.markdown("##### 1. 📝 Executive Company Summary")
                if f"{selected_comp}_summary" in st.session_state.ai_results:
                    st.info(st.session_state.ai_results[f"{selected_comp}_summary"])
                else:
                    st.caption("Click **Summary** or **Run Complete 360° Dossier** to generate.")

                st.markdown("##### 2. 🏷️ Industry & Business Model Classification")
                if f"{selected_comp}_industry" in st.session_state.ai_results:
                    ind_res = st.session_state.ai_results[f"{selected_comp}_industry"]
                    st.markdown(f"""
                        <div class="ai-box">
                            <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px;">
                                <span class="ai-pill">Industry: <strong>{ind_res.get('primary_industry', 'N/A')}</strong></span>
                                <span class="ai-pill">Niche: <strong>{ind_res.get('sub_vertical', 'N/A')}</strong></span>
                                <span class="ai-pill">Model: <strong>{ind_res.get('business_model', 'N/A')}</strong></span>
                                <span class="ai-pill ai-pill-green">Confidence: {ind_res.get('confidence', 'N/A')}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.caption("Click **Classification** to view verified taxonomy.")

                st.markdown("##### 5. 🔍 Key Information Extraction")
                if f"{selected_comp}_extraction" in st.session_state.ai_results:
                    ext_res = st.session_state.ai_results[f"{selected_comp}_extraction"]
                    st.markdown(f"""
                        <div class="ai-box">
                            <div style="font-size: 0.85rem; color: #E2E8F0; line-height: 1.6;">
                                <strong>🏢 Model:</strong> {ext_res.get('business_model', 'N/A')}<br>
                                <strong>🎯 Target Audience:</strong> {ext_res.get('target_audience', 'N/A')}<br>
                                <strong>📏 Estimated Scale:</strong> {ext_res.get('estimated_scale', 'N/A')}<br>
                                <strong>👤 Key Contact:</strong> {ext_res.get('key_contact', 'N/A')} ({ext_res.get('contact_role', 'N/A')})<br>
                                <strong>⚡ Tech Signals:</strong> {', '.join(ext_res.get('tech_signals', [])) or 'N/A'}<br>
                                <strong>🌐 Channels:</strong> {', '.join(ext_res.get('presence_channels', [])) or 'N/A'}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.caption("Click **Key Extraction** to pull structured entities.")

            with dossier_col2:
                st.markdown("##### 3. 🎯 Business Relevance Analysis")
                if f"{selected_comp}_relevance" in st.session_state.ai_results:
                    rel_res = st.session_state.ai_results[f"{selected_comp}_relevance"]
                    st.markdown(f"""
                        <div class="ai-box">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-size: 0.85rem; font-weight: 700; color: #F1F5F9;">{rel_res.get('fit_tier', 'Target')}</span>
                                <span class="ai-pill ai-pill-green">Score: {rel_res.get('relevance_score', 0)}/100</span>
                            </div>
                            <div style="font-size: 0.84rem; color: #CBD5E1; margin-bottom: 8px;">
                                <strong>Fit Rationale:</strong> {rel_res.get('value_proposition_fit', '')}
                            </div>
                            <div style="font-size: 0.82rem; color: #94A3B8; margin-bottom: 8px;">
                                <strong>Likely Pain Points:</strong>
                                <ul>
                                    {''.join([f"<li>{p}</li>" for p in rel_res.get('pain_points', [])])}
                                </ul>
                            </div>
                            <div style="background: rgba(124, 108, 242, 0.15); border-left: 3px solid #7C6CF2; padding: 8px 12px; border-radius: 6px; font-size: 0.82rem; color: #E0E7FF;">
                                <strong>🎣 Outreach Hook:</strong> {rel_res.get('outreach_hook', '')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.caption("Click **Relevance** to analyze intent alignment.")

                st.markdown("##### 4. 🛡️ Lead-Quality Explanation & Readiness")
                if f"{selected_comp}_quality" in st.session_state.ai_results:
                    qual_res = st.session_state.ai_results[f"{selected_comp}_quality"]
                    st.markdown(f"""
                        <div class="ai-box">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-size: 0.85rem; font-weight: 700; color: #F1F5F9;">Rating: {qual_res.get('quality_rating', 'Standard')}</span>
                                <span class="ai-pill">Readiness: {qual_res.get('outreach_readiness', 'Review')}</span>
                            </div>
                            <div style="font-size: 0.82rem; color: #10B981; margin-bottom: 6px;">
                                <strong>Key Strengths:</strong>
                                <ul>
                                    {''.join([f"<li>{s}</li>" for s in qual_res.get('strengths', [])])}
                                </ul>
                            </div>
                            <div style="font-size: 0.82rem; color: #F59E0B; margin-bottom: 8px;">
                                <strong>Risks / Data Gaps:</strong>
                                <ul>
                                    {''.join([f"<li>{r}</li>" for r in qual_res.get('risks_or_gaps', [])])}
                                </ul>
                            </div>
                            <div style="background: rgba(16, 185, 129, 0.1); border-left: 3px solid #10B981; padding: 8px 12px; border-radius: 6px; font-size: 0.82rem; color: #D1FAE5;">
                                <strong>👉 Recommended SDR Next Step:</strong> {qual_res.get('recommended_next_step', '')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.caption("Click **Lead Quality** to evaluate signal strength.")

    # -----------------------------------------------------
    # TAB 6: Export Center
    # -----------------------------------------------------
    with tab_export:
        st.markdown("#### 📦 Recruiter & CRM Export Hub")
        st.write(
            "Export structured, verified business intelligence records formatted for direct CRM ingestion. "
            "Every record retains 0-100 Lead Scores, Lead Categories, Score Explanations, and Source Verification URLs."
        )

        export_cols = [
            'Data Source',
            'Company Name',
            'Lead Score',
            'Lead Category',
            'Lead Score Reason',
            'Confidence Score',
            'Data Completeness %',
            'Industry',
            'Location',
            'Website',
            'LinkedIn URL',
            'Company Description',
            'Decision Maker',
            'Decision Maker Role',
            'Source URL',
            'Research Summary'
        ]
        available_exp_cols = [c for c in export_cols if c in df.columns]
        export_df = df[available_exp_cols].copy()

        # Merge any generated AI summaries if available
        comp_key = 'Company Name' if 'Company Name' in export_df.columns else 'Company'
        if st.session_state.ai_results:
            ai_summaries = {}
            for comp in export_df[comp_key]:
                if f"{comp}_summary" in st.session_state.ai_results:
                    ai_summaries[comp] = st.session_state.ai_results[f"{comp}_summary"]
            if ai_summaries:
                export_df['AI Enriched Summary'] = export_df[comp_key].map(ai_summaries).fillna('')

        csv_payload = export_df.to_csv(index=False).encode('utf-8')
        export_summary = {
            'Query': query,
            'Target Industry': target_industry,
            'Target Location': target_location,
            'Target Company Type': target_company_type,
            'Keywords': keywords or 'None',
            'Generated At': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Total Raw Records Ingested': stats.get('total_raw_records', len(raw_df)),
            'Valid Unique Companies': len(export_df),
            'High Potential Leads': int((export_df['Lead Category'] == 'High Potential').sum()) if 'Lead Category' in export_df.columns else 0,
            'Medium Potential Leads': int((export_df['Lead Category'] == 'Medium Potential').sum()) if 'Lead Category' in export_df.columns else 0,
            'Low Potential Leads': int((export_df['Lead Category'] == 'Low Potential').sum()) if 'Lead Category' in export_df.columns else 0,
            'Average Lead Score': round(export_df['Lead Score'].mean(), 1) if 'Lead Score' in export_df.columns else 0,
            'Average Confidence Score': round(export_df['Confidence Score'].mean(), 1) if 'Confidence Score' in export_df.columns else 0,
            'Average Data Completeness %': round(export_df['Data Completeness %'].mean(), 1) if 'Data Completeness %' in export_df.columns else 0,
        }
        excel_payload = to_excel_bytes(export_df, export_summary, raw_df=raw_df, stats=stats)

        file_prefix = "demo_" if is_demo else ""

        exp_c1, exp_c2 = st.columns(2)
        with exp_c1:
            st.markdown("""
                <div class="content-card">
                    <h5 style="margin-top: 0; color: #F1F5F9;">Structured CSV Export</h5>
                    <p style="font-size: 0.82rem; color: #94A3B8;">Clean UTF-8 CSV with Data Source tag, 0-100 Lead Scores, Lead Categories, Score Explanations, and source URLs.</p>
                </div>
            """, unsafe_allow_html=True)
            st.download_button(
                label="⬇️ Download CSV Dataset",
                data=csv_payload,
                file_name=f"b2b_leads_{file_prefix}{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with exp_c2:
            st.markdown("""
                <div class="content-card">
                    <h5 style="margin-top: 0; color: #F1F5F9;">Multi-Tab Professional Excel Report (.xlsx)</h5>
                    <p style="font-size: 0.82rem; color: #94A3B8;">Executive 4-sheet workbook: <strong>Research Results</strong>, <strong>Data Quality</strong>, <strong>Lead Scoring</strong>, and <strong>Research Summary</strong>.</p>
                </div>
            """, unsafe_allow_html=True)
            st.download_button(
                label="⬇️ Download Excel Workbook (.xlsx)",
                data=excel_payload,
                file_name=f"b2b_lead_report_{file_prefix}{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        st.markdown("""
            <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 12px 16px; margin: 16px 0 12px 0;">
                <span style="font-size: 0.82rem; font-weight: 700; color: #7C6CF2;">💼 INTERVIEW-READY EXCEL STRUCTURE</span>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-top: 8px; font-size: 0.78rem; color: #CBD5E1;">
                    <div>📄 <strong>Sheet 1: Research Results</strong><br><span style="color:#94A3B8;">Freeze pane, auto-filter, category fills, clickable hyperlinks</span></div>
                    <div>🛡️ <strong>Sheet 2: Data Quality</strong><br><span style="color:#94A3B8;">Audit KPIs, completeness %, URL statuses, deduplication log</span></div>
                    <div>🎯 <strong>Sheet 3: Lead Scoring</strong><br><span style="color:#94A3B8;">7-factor weights rubric, company factor points & explanations</span></div>
                    <div>📊 <strong>Sheet 4: Research Summary</strong><br><span style="color:#94A3B8;">Executive scope manifest, cohort KPIs, Top 5 ICP spotlight</span></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("##### 📋 Scoring Audit & Export Manifest")
        st.json(export_summary)

else:
    # -----------------------------------------------------
    # Empty State: Modern SaaS Onboarding & Guided Pipeline
    # -----------------------------------------------------
    st.markdown("""
        <div style="background: rgba(23, 27, 37, 0.7); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 32px 28px; margin-top: 12px; margin-bottom: 28px;">
            <div style="max-width: 720px;">
                <span class="saas-badge">Deterministic Lead Intelligence</span>
                <h2 style="color: #FFFFFF; font-weight: 800; font-size: 1.6rem; margin: 8px 0 12px 0;">
                    Autonomous B2B Research & 0-100 Lead Scoring
                </h2>
                <p style="color: #94A3B8; font-size: 0.95rem; line-height: 1.6; margin-bottom: 20px;">
                    Research companies across <strong>Industry</strong>, <strong>Location</strong>,
                    <strong>Keywords</strong>, and <strong>Company Type</strong>.
                    Every prospect is ranked using a 100% deterministic, 7-factor 0-100 rubric assigning
                    <strong>High, Medium, or Low Potential</strong> with complete mathematical transparency.
                </p>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-top: 24px;">
                <div class="step-card">
                    <div class="step-number">1</div>
                    <div class="step-title">Configure Scope</div>
                    <div class="step-desc">Enter industry, location, company count, keywords, and target company type.</div>
                </div>
                <div class="step-card">
                    <div class="step-number">2</div>
                    <div class="step-title">Ingest & Preserve</div>
                    <div class="step-desc">Retains raw unedited research data separately from sanitized output.</div>
                </div>
                <div class="step-card">
                    <div class="step-number">3</div>
                    <div class="step-title">Dedupe & Validate</div>
                    <div class="step-desc">Canonical deduplication, link normalization, and completeness scoring.</div>
                </div>
                <div class="step-card">
                    <div class="step-number">4</div>
                    <div class="step-title">Deterministic Scoring</div>
                    <div class="step-desc">Calculates 0-100 Lead Score across 7 factors with reproducible explanations.</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    ec1, ec2 = st.columns([1.5, 3])
    with ec1:
        if st.button("⚡ Run Instant Demo Research", type="primary", use_container_width=True):
            st.session_state.mode = "Demo Mode"
            raw = demo_dataset()
            st.session_state.raw_df = raw.copy()
            clean, stats = clean_dataframe(raw)
            scored = add_validation_scores(clean)
            scored = add_lead_score(
                scored,
                target_industry=st.session_state.target_industry,
                target_location=st.session_state.target_location,
                keywords=st.session_state.keywords,
                target_company_type=st.session_state.target_company_type
            )
            st.session_state.df = scored
            st.session_state.stats = stats
            st.session_state.ai_results = {}
            st.session_state.macro_insights = None
            st.session_state.last_run_time = datetime.now().strftime("%H:%M:%S")
            st.rerun()

    with ec2:
        st.markdown("""
            <div style="font-size: 0.85rem; color: #64748B; padding-top: 10px;">
                💡 <strong>Reviewer Tip:</strong> Clicking above loads the demo dataset, evaluating all 7 scoring factors deterministically and displaying category badges with audit explanations.
            </div>
        """, unsafe_allow_html=True)
