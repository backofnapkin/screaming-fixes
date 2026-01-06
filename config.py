"""
Configuration for Screaming Fixes Landing Pages
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as this config file (for local dev)
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


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
