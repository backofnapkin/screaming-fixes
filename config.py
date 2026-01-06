"""
Configuration for Screaming Fixes
Central configuration for the main app and landing pages.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as this config file (for local dev)
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


# =============================================================================
# QUICK START MODE CONFIGURATION
# =============================================================================

QUICK_START_API_KEY = os.environ.get("AGENT_MODE_API_KEY", "")  # Your key for free AI suggestions
QUICK_START_FREE_SUGGESTIONS = 5  # Number of free AI suggestions in Quick Start Mode
QUICK_START_PAGE_LIMIT = 25  # Max pages in Quick Start Mode

# Legacy aliases for backwards compatibility
AGENT_MODE_API_KEY = QUICK_START_API_KEY
AGENT_MODE_FREE_SUGGESTIONS = QUICK_START_FREE_SUGGESTIONS
AGENT_MODE_LIMIT = QUICK_START_PAGE_LIMIT

# Analytics configuration (silent tracking)
LANGSMITH_ENABLED = os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true"


def get_secret(key: str, default: str = "") -> str:
    """
    Get a secret from Streamlit secrets (cloud) or environment variables (local).
    Streamlit Cloud uses st.secrets, local dev uses .env
    """
    # First try environment variables (works for local .env)
    value = os.environ.get(key, "")
    if value:
        return value

    # Then try Streamlit secrets (for Streamlit Cloud)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass

    return default


# =============================================================================
# SUPABASE CONFIGURATION
# =============================================================================

SUPABASE_URL = get_secret("SUPABASE_URL", "https://yybfjsjysfteqjvicuuy.supabase.co")
SUPABASE_KEY = get_secret("SUPABASE_KEY", "")

# =============================================================================
# DATAFORSEO CONFIGURATION
# =============================================================================

DATAFORSEO_LOGIN = get_secret("DATAFORSEO_LOGIN", "")
DATAFORSEO_PASSWORD = get_secret("DATAFORSEO_PASSWORD", "")

# Use mock data if DataForSEO credentials are not configured
USE_MOCK_DATA = not (DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD)

# =============================================================================
# BRANDING
# =============================================================================

PRIMARY_TEAL = "#14b8a6"
PRIMARY_TEAL_DARK = "#0d9488"
PRIMARY_TEAL_DARKER = "#0f766e"

# =============================================================================
# FEATURE FLAGS
# =============================================================================

# Landing page features
RECLAIM_TEASER_COUNT = 3  # Number of results to show before email capture
RECLAIM_MIN_BROKEN = 30  # Minimum mock broken backlinks
RECLAIM_MAX_BROKEN = 60  # Maximum mock broken backlinks

# Rate limiting for abuse prevention
RECLAIM_SESSION_LIMIT = 3  # Max scans per browser session
RECLAIM_IP_DAILY_LIMIT = 5  # Max scans per IP address per day


# =============================================================================
# MAIN APP CSS
# =============================================================================

def get_app_css() -> str:
    """Get the main app CSS styles - consistent teal/cyan color scheme"""
    return """
<style>
    /* Import clean font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global font */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main header with gradient accent */
    .main-header {
        font-size: 2.75rem;
        font-weight: 700;
        background: linear-gradient(135deg, #0d9488 0%, #0891b2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.25rem;
        letter-spacing: -0.02em;
    }

    .tagline {
        font-size: 1.2rem;
        color: #64748b;
        margin-bottom: 1.5rem;
        font-weight: 400;
    }

    .intro-text {
        font-size: 1.05rem;
        line-height: 1.75;
        color: #475569;
        margin-bottom: 1.5rem;
    }

    .intro-text strong {
        color: #0d9488;
        font-weight: 600;
    }

    /* Section headers with teal accent */
    .section-header {
        font-size: 2.25rem;
        font-weight: 600;
        color: #134e4a;
        margin-top: 2.5rem;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid #99f6e4;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .section-header::before {
        content: '';
        display: inline-block;
        width: 5px;
        height: 36px;
        background: linear-gradient(180deg, #14b8a6 0%, #0891b2 100%);
        border-radius: 2px;
        margin-right: 10px;
    }

    /* Privacy notice card */
    .privacy-notice {
        padding: 1rem 1.25rem;
        background: linear-gradient(135deg, #f0fdfa 0%, #ecfeff 100%);
        border-radius: 12px;
        font-size: 0.9rem;
        margin-bottom: 1.25rem;
        border: 1px solid #99f6e4;
        color: #134e4a;
    }

    .privacy-notice strong {
        color: #0d9488;
    }

    /* Card styling for expanders */
    .stExpander {
        border: 1px solid #ccfbf1 !important;
        border-radius: 12px !important;
        background: #ffffff !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }

    .stExpander:hover {
        border-color: #5eead4 !important;
        box-shadow: 0 4px 6px rgba(20, 184, 166, 0.08) !important;
    }

    /* Button styling */
    .stButton > button {
        width: 100%;
        border-radius: 8px !important;
        font-weight: 500 !important;
        padding: 0.6rem 1.25rem !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%) !important;
        border: none !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%) !important;
        box-shadow: 0 4px 12px rgba(20, 184, 166, 0.35) !important;
    }

    .stButton > button[kind="secondary"] {
        background: #ffffff !important;
        border: 1px solid #99f6e4 !important;
        color: #0d9488 !important;
    }

    .stButton > button[kind="secondary"]:hover {
        background: #f0fdfa !important;
        border-color: #14b8a6 !important;
        color: #0f766e !important;
    }

    /* Input fields */
    .stTextInput > div > div > input {
        border-radius: 8px !important;
        border: 1px solid #ccfbf1 !important;
        padding: 0.6rem 0.875rem !important;
        transition: all 0.2s ease !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #14b8a6 !important;
        box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.15) !important;
    }

    /* Success/Info/Warning boxes */
    .stSuccess {
        background: linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 100%) !important;
        border: 1px solid #5eead4 !important;
        border-radius: 8px !important;
        color: #134e4a !important;
    }

    .stInfo {
        background: linear-gradient(135deg, #f0fdfa 0%, #ecfeff 100%) !important;
        border: 1px solid #99f6e4 !important;
        border-radius: 8px !important;
        color: #134e4a !important;
    }

    .stWarning {
        background: linear-gradient(135deg, #fefce8 0%, #fef9c3 100%) !important;
        border: 1px solid #fde047 !important;
        border-radius: 8px !important;
    }

    /* Metrics styling */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #f0fdfa 0%, #ffffff 100%);
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid #ccfbf1;
    }

    [data-testid="stMetricLabel"] {
        color: #0d9488 !important;
    }

    [data-testid="stMetricValue"] {
        color: #134e4a !important;
        font-weight: 600 !important;
    }

    /* DataFrame styling */
    .stDataFrame {
        border-radius: 12px !important;
        overflow: hidden !important;
        border: 1px solid #ccfbf1 !important;
    }

    /* File uploader - taller drop zone */
    [data-testid="stFileUploader"] {
        border: 2px dashed #99f6e4 !important;
        border-radius: 12px !important;
        padding: 2rem 1rem !important;
        min-height: 180px !important;
        transition: all 0.2s ease !important;
    }

    [data-testid="stFileUploader"] section {
        padding: 1.5rem 0 !important;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: #14b8a6 !important;
        background: #f0fdfa !important;
    }

    /* Navigation links */
    nav a, .nav-link {
        color: #64748b;
        transition: color 0.2s ease;
    }

    nav a:hover, .nav-link:hover {
        color: #0d9488;
    }

    /* Links in body text */
    a {
        color: #0d9488;
    }

    a:hover {
        color: #0f766e;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Smooth scrolling */
    html {
        scroll-behavior: smooth;
    }

    /* Download button styling */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 100%) !important;
        border: 1px solid #5eead4 !important;
        color: #0d9488 !important;
    }

    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #ccfbf1 0%, #99f6e4 100%) !important;
        border-color: #14b8a6 !important;
        color: #0f766e !important;
    }

    /* Checkbox styling - teal theme */
    .stCheckbox > label > span {
        color: #0d9488 !important;
    }

    .stCheckbox input[type="checkbox"]:checked + div {
        background-color: #0d9488 !important;
        border-color: #0d9488 !important;
    }

    /* Streamlit checkbox checked state */
    [data-testid="stCheckbox"] [data-checked="true"] {
        background-color: #0d9488 !important;
    }

    /* Radio button styling - teal theme */
    .stRadio > div[role="radiogroup"] > label > div:first-child {
        border-color: #14b8a6 !important;
    }

    .stRadio > div[role="radiogroup"] > label[data-checked="true"] > div:first-child {
        background-color: #0d9488 !important;
        border-color: #0d9488 !important;
    }

    /* Footer */
    .footer {
        text-align: center;
        color: #64748b;
        font-size: 0.875rem;
        padding: 2rem 0 1rem 0;
    }

    .footer a {
        color: #0d9488;
        text-decoration: none;
    }

    .footer a:hover {
        color: #0f766e;
        text-decoration: underline;
    }

    /* Custom spreadsheet row */
    .url-row {
        background: linear-gradient(135deg, #f0fdfa 0%, #ffffff 100%);
        border: 1px solid #ccfbf1;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
    }

    .url-row:hover {
        border-color: #5eead4;
    }

    .url-text {
        font-family: 'SF Mono', 'Fira Code', monospace;
        font-size: 0.8rem;
        color: #134e4a;
        word-break: break-all;
    }

    .status-badge {
        display: inline-block;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }

    .status-4xx {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        color: #dc2626;
    }

    .status-internal {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        color: #059669;
    }

    .status-external {
        background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
        color: #475569;
    }

    .anchor-preview {
        background: #f8fafc;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        color: #64748b;
        font-style: italic;
    }

    .ai-notes {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border-left: 3px solid #f59e0b;
        padding: 0.5rem 0.75rem;
        border-radius: 0 6px 6px 0;
        font-size: 0.8rem;
        color: #92400e;
        margin-top: 0.5rem;
    }

    .approved-badge {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        color: #059669;
        padding: 0.25rem 0.75rem;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    .pending-badge {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        color: #b45309;
        padding: 0.25rem 0.75rem;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    .ignored-badge {
        background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
        color: #64748b;
        padding: 0.25rem 0.75rem;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    /* Feature Cards */
    .feature-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        transition: all 0.2s ease;
        cursor: pointer;
        height: 100%;
    }

    .feature-card:hover {
        border-color: #14b8a6;
        box-shadow: 0 4px 12px rgba(20, 184, 166, 0.15);
        transform: translateY(-2px);
    }

    .feature-card.ready {
        border-color: #a7f3d0;
        background: linear-gradient(135deg, #f0fdfa 0%, #ffffff 100%);
    }

    .feature-card.locked {
        border-color: #e2e8f0;
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        opacity: 0.85;
    }

    .feature-card-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }

    .feature-card-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #134e4a;
        margin-bottom: 0.35rem;
    }

    .feature-card-desc {
        font-size: 0.85rem;
        color: #64748b;
        margin-bottom: 0.75rem;
        line-height: 1.4;
    }

    .feature-card-status {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .feature-card-status.ready {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        color: #059669;
    }

    .feature-card-status.locked {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        color: #b45309;
    }

    /* Integration Row */
    .integration-row {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
    }

    .integration-row.connected {
        border-color: #a7f3d0;
        background: linear-gradient(135deg, #f0fdfa 0%, #ffffff 100%);
    }

    .integration-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }

    .integration-title {
        font-weight: 600;
        color: #134e4a;
        font-size: 1rem;
    }

    .integration-status {
        font-size: 0.8rem;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
    }

    .integration-status.connected {
        background: #d1fae5;
        color: #059669;
    }

    .integration-status.not-connected {
        background: #fef3c7;
        color: #b45309;
    }

    .integration-desc {
        font-size: 0.85rem;
        color: #64748b;
        margin-bottom: 0.75rem;
    }
</style>
"""
