"""
Configuration for Screaming Fixes Landing Pages
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as this config file
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# =============================================================================
# SUPABASE CONFIGURATION
# =============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://yybfjsjysfteqjvicuuy.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# =============================================================================
# DATAFORSEO CONFIGURATION
# =============================================================================

DATAFORSEO_LOGIN = os.environ.get("DATAFORSEO_LOGIN", "")
DATAFORSEO_PASSWORD = os.environ.get("DATAFORSEO_PASSWORD", "")

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
