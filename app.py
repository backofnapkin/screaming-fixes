"""
Screaming Fixes v3 - AI-Powered WordPress Broken Link Fixer
Built with Streamlit

Upload your Screaming Frog CSV export → Review unique broken URLs → 
Get AI suggestions → Approve fixes → Apply to WordPress
"""

import os
import io
import json
import re
import time
from datetime import datetime
from typing import Optional, Dict, List, Any
from urllib.parse import urlparse
from collections import defaultdict

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Agent Mode configuration
AGENT_MODE_API_KEY = os.environ.get("AGENT_MODE_API_KEY", "")  # Your key for free AI suggestions
AGENT_MODE_FREE_SUGGESTIONS = 5  # Number of free AI suggestions in Agent Mode

# Analytics configuration (silent tracking)
LANGSMITH_ENABLED = os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true"

# Page config
st.set_page_config(
    page_title="Screaming Fixes",
    page_icon="🔧",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Optional imports
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from wordpress_client import WordPressClient
    WP_AVAILABLE = True
except ImportError:
    WP_AVAILABLE = False

# LangSmith tracking (optional)
try:
    from langsmith import Client as LangSmithClient
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False


def track_event(event_name: str, metadata: Dict = None):
    """Track an analytics event to LangSmith (silent, non-blocking)"""
    if not LANGSMITH_ENABLED or not LANGSMITH_AVAILABLE:
        return
    
    try:
        client = LangSmithClient()
        client.create_run(
            name=event_name,
            run_type="chain",
            inputs=metadata or {},
            project_name=os.environ.get("LANGCHAIN_PROJECT", "screaming-fixes"),
        )
    except Exception:
        pass  # Silent fail - don't interrupt user experience


# =============================================================================
# CUSTOM CSS - Consistent teal/cyan color scheme from v1
# =============================================================================

st.markdown("""
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
</style>
""", unsafe_allow_html=True)


# =============================================================================
# CONSTANTS
# =============================================================================

AGENT_MODE_LIMIT = 25  # Max source pages for automatic Post ID lookup


# =============================================================================
# SESSION STATE
# =============================================================================

def init_session_state():
    """Initialize session state"""
    defaults = {
        # Task type management
        'task_type': None,  # 'broken_links' or 'redirect_chains'
        'current_task': 'broken_links',  # Which task is currently active
        
        # Broken Links data
        'df': None,
        'domain': None,
        'broken_urls': {},
        'decisions': {},
        
        # Redirect Chains data
        'rc_df': None,
        'rc_domain': None,
        'rc_redirects': {},  # Grouped redirect data
        'rc_decisions': {},
        'rc_sitewide': [],  # Sitewide links (informational)
        'rc_loops': [],  # Loop redirects (informational)
        
        # Redirect Chain filters
        'rc_filter_301': True,
        'rc_filter_302': True,
        'rc_filter_hops': 'all',  # 'all', '1', '2', '3+'
        'rc_show_approved': True,
        'rc_show_pending': True,
        'rc_page': 0,
        'rc_editing_url': None,
        
        # WordPress connection (shared)
        'wp_connected': False,
        'wp_client': None,
        'wp_preview_results': None,
        'wp_execute_results': None,
        'wp_preview_done': False,
        'wp_was_test_run': False,  # Track if last execution was a test run
        'selected_mode': 'agent',  # 'agent' or 'enterprise'
        'anthropic_key': '',  # User's own API key (for Enterprise Mode)
        'ai_suggestions_remaining': AGENT_MODE_FREE_SUGGESTIONS,  # Free suggestions in Agent Mode
        
        # Broken Links UI state
        'page': 0,
        'per_page': 10,
        'filter_internal': True,
        'filter_external': True,
        'show_approved': True,
        'show_pending': True,
        'bulk_action': None,  # For bulk action confirmation
        'sort_by': 'impact',  # Sort option: impact, status_code, internal_first
        'editing_url': None,  # Currently editing URL (for inline edit form)
        
        # Post ID tracking (shared)
        'has_post_ids': False,  # CSV included post_id column
        'source_pages_count': 0,  # Total unique source pages
        'post_id_check_done': False,  # Sample check completed
        'post_id_check_passed': False,  # Sample check found Post IDs
        'post_id_cache': {},  # Cache of URL -> Post ID (found or manual)
        'agent_mode_available': False,  # ≤25 pages and check passed, or has_post_ids
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# =============================================================================
# DATA PROCESSING
# =============================================================================

def detect_domain(urls: List[str]) -> Optional[str]:
    """Detect primary domain from URLs"""
    counts = defaultdict(int)
    for url in urls:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace('www.', '')
            if domain:
                counts[domain] += 1
        except:
            pass
    return max(counts, key=counts.get) if counts else None


def is_internal(url: str, domain: str) -> bool:
    """Check if URL is internal"""
    if not domain:
        return True
    try:
        parsed = urlparse(url)
        url_domain = parsed.netloc.lower().replace('www.', '')
        return domain in url_domain or url_domain in domain
    except:
        return False


def parse_csv(uploaded_file) -> Optional[pd.DataFrame]:
    """Parse uploaded CSV"""
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip()
        
        required = ['Source', 'Destination', 'Status Code']
        missing = [c for c in required if c not in df.columns]
        if missing:
            st.error(f"Missing columns: {', '.join(missing)}")
            return None
        
        # Check for post_id column (case-insensitive)
        post_id_col = None
        for col in df.columns:
            if col.lower().replace('_', '').replace(' ', '') in ['postid', 'post_id', 'id']:
                post_id_col = col
                break
        
        if post_id_col:
            df['post_id'] = pd.to_numeric(df[post_id_col], errors='coerce')
            valid_ids = df['post_id'].notna().sum()
            st.success(f"✅ Found Post ID column: **{valid_ids}** valid IDs detected")
        else:
            df['post_id'] = None
        
        if 'Link Position' in df.columns:
            before = len(df)
            df = df[df['Link Position'] == 'Content'].copy()
            filtered = before - len(df)
            if filtered > 0:
                st.info(f"📍 Filtered to Content links only ({filtered} non-content links excluded for safety)")
        
        return df
    except Exception as e:
        st.error(f"Error parsing CSV: {e}")
        return None


def detect_csv_type(df: pd.DataFrame) -> str:
    """Auto-detect if CSV is broken links or redirect chains based on columns"""
    columns = set(df.columns.str.lower().str.strip())
    
    # Redirect chains has these distinctive columns
    redirect_chain_indicators = {'final address', 'number of redirects', 'chain type', 'loop'}
    
    # Broken links has these columns
    broken_link_indicators = {'destination', 'status code'}
    
    # Check for redirect chains first (more specific)
    if len(redirect_chain_indicators & columns) >= 2:
        return 'redirect_chains'
    
    # Fall back to broken links
    if len(broken_link_indicators & columns) >= 2:
        return 'broken_links'
    
    # Default to broken links if unclear
    return 'broken_links'


def parse_redirect_chains_csv(uploaded_file) -> Optional[pd.DataFrame]:
    """Parse uploaded Redirect Chains CSV from Screaming Frog"""
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip()
        
        # Required columns for redirect chains
        required = ['Source', 'Address', 'Final Address']
        missing = [c for c in required if c not in df.columns]
        if missing:
            st.error(f"Missing columns: {', '.join(missing)}")
            return None
        
        # Ensure we have the key columns with defaults
        if 'Number of Redirects' not in df.columns:
            df['Number of Redirects'] = 1
        if 'Loop' not in df.columns:
            df['Loop'] = False
        if 'Link Position' not in df.columns:
            df['Link Position'] = 'Content'
        if 'Temp Redirect in Chain' not in df.columns:
            df['Temp Redirect in Chain'] = False
        if 'Anchor Text' not in df.columns:
            df['Anchor Text'] = ''
        
        # Convert Loop column to boolean
        df['Loop'] = df['Loop'].astype(str).str.upper() == 'TRUE'
        
        # Convert Temp Redirect to boolean  
        df['Temp Redirect in Chain'] = df['Temp Redirect in Chain'].astype(str).str.upper() == 'TRUE'
        
        # Check for post_id column (case-insensitive)
        post_id_col = None
        for col in df.columns:
            if col.lower().replace('_', '').replace(' ', '') in ['postid', 'post_id', 'id']:
                post_id_col = col
                break
        
        if post_id_col:
            df['post_id'] = pd.to_numeric(df[post_id_col], errors='coerce')
            valid_ids = df['post_id'].notna().sum()
            st.success(f"✅ Found Post ID column: **{valid_ids}** valid IDs detected")
        else:
            df['post_id'] = None
        
        return df
    except Exception as e:
        st.error(f"Error parsing CSV: {e}")
        return None


def group_redirect_chains(df: pd.DataFrame, domain: str) -> tuple:
    """
    Group redirect chains by unique Address -> Final Address pairs.
    Also separates out sitewide links and loops.
    
    Returns: (redirects_dict, sitewide_list, loops_list)
    """
    redirects = {}
    sitewide = []
    loops = []
    
    for _, row in df.iterrows():
        address = row['Address']
        final_address = row['Final Address']
        source = row['Source']
        link_position = row.get('Link Position', 'Content')
        is_loop = row.get('Loop', False)
        is_temp = row.get('Temp Redirect in Chain', False)
        num_hops = int(row.get('Number of Redirects', 1))
        anchor = row.get('Anchor Text', '')
        
        # Handle loops separately
        if is_loop:
            loops.append({
                'address': address,
                'final_address': final_address,
                'source': source,
                'anchor': anchor,
                'hops': num_hops
            })
            continue
        
        # Handle sitewide (non-Content) links separately
        if link_position and link_position.lower() not in ['content', '']:
            sitewide.append({
                'address': address,
                'final_address': final_address,
                'source': source,
                'position': link_position,
                'anchor': anchor
            })
            continue
        
        # Create unique key for this redirect pair
        key = f"{address}|||{final_address}"
        
        if key not in redirects:
            redirects[key] = {
                'address': address,
                'final_address': final_address,
                'is_internal': is_internal(address, domain),
                'is_temp_redirect': is_temp,
                'num_hops': num_hops,
                'anchors': [],
                'sources': [],
                'source_post_ids': {},
                'count': 0
            }
        
        redirects[key]['count'] += 1
        
        if anchor and anchor not in redirects[key]['anchors']:
            redirects[key]['anchors'].append(anchor)
        
        if source not in redirects[key]['sources']:
            redirects[key]['sources'].append(source)
        
        # Store post_id if available
        if pd.notna(row.get('post_id')):
            redirects[key]['source_post_ids'][source] = int(row['post_id'])
        
        # Update temp redirect status if any in chain is temp
        if is_temp:
            redirects[key]['is_temp_redirect'] = True
    
    # Consolidate sitewide links by address
    sitewide_consolidated = {}
    for item in sitewide:
        key = item['address']
        if key not in sitewide_consolidated:
            sitewide_consolidated[key] = {
                'address': item['address'],
                'final_address': item['final_address'],
                'position': item['position'],
                'sources': [],
                'count': 0
            }
        sitewide_consolidated[key]['sources'].append(item['source'])
        sitewide_consolidated[key]['count'] += 1
    
    # Consolidate loops by address
    loops_consolidated = {}
    for item in loops:
        key = item['address']
        if key not in loops_consolidated:
            loops_consolidated[key] = {
                'address': item['address'],
                'final_address': item['final_address'],
                'sources': [],
                'count': 0
            }
        loops_consolidated[key]['sources'].append(item['source'])
        loops_consolidated[key]['count'] += 1
    
    return redirects, list(sitewide_consolidated.values()), list(loops_consolidated.values())


def group_by_broken_url(df: pd.DataFrame, domain: str) -> Dict[str, Dict]:
    """Group data by unique broken URL"""
    grouped = {}
    
    for _, row in df.iterrows():
        dest = row['Destination']
        
        if dest not in grouped:
            grouped[dest] = {
                'status_code': row['Status Code'],
                'status_text': row.get('Status', ''),
                'is_internal': is_internal(dest, domain),
                'anchors': [],
                'sources': [],
                'source_post_ids': {},  # Map source URL to post_id
                'count': 0
            }
        
        grouped[dest]['count'] += 1
        
        anchor = row.get('Anchor', '')
        if anchor and anchor not in grouped[dest]['anchors']:
            grouped[dest]['anchors'].append(anchor)
        
        source = row['Source']
        if source not in grouped[dest]['sources']:
            grouped[dest]['sources'].append(source)
        
        # Store post_id if available
        if pd.notna(row.get('post_id')):
            grouped[dest]['source_post_ids'][source] = int(row['post_id'])
    
    return grouped


# =============================================================================
# AI SUGGESTIONS
# =============================================================================

def get_ai_suggestion(broken_url: str, info: Dict, domain: str, api_key: str) -> Dict[str, str]:
    """Get AI suggestion for a single broken URL with web search"""
    
    # Track AI suggestion request (no URLs/PII)
    is_agent_mode_key = api_key == AGENT_MODE_API_KEY
    track_event("ai_suggestion_request", {
        "is_agent_mode_key": is_agent_mode_key,
        "is_internal": info['is_internal'],
        "status_code": info['status_code'],
        "affected_pages": info['count']
    })
    
    if not ANTHROPIC_AVAILABLE:
        return {'action': 'remove', 'url': None, 'notes': 'Anthropic library not installed.'}
    
    try:
        client = Anthropic(api_key=api_key)
        
        anchors_text = ', '.join(f'"{a}"' for a in info['anchors'][:5])
        if len(info['anchors']) > 5:
            anchors_text += f' (+{len(info["anchors"]) - 5} more)'
        
        type_label = "internal" if info['is_internal'] else "external"
        
        prompt = f"""You are helping fix broken links on {domain}.

BROKEN URL: {broken_url}
STATUS: {info['status_code']} {info['status_text']}
TYPE: {type_label}
ANCHOR TEXTS USED: {anchors_text}
APPEARS ON: {info['count']} page(s)

Your task:
1. If INTERNAL, search {domain} to find if similar content exists at a different URL
2. If EXTERNAL, check if the content has moved to a new URL
3. Recommend REMOVE (delete link, keep anchor text) or REPLACE (with specific URL)

IMPORTANT:
- Only suggest REPLACE if you find a real working URL
- Default to REMOVE if no good replacement exists
- Keep notes to 1-2 sentences

Respond in JSON format:
{{"action": "remove" or "replace", "url": "replacement URL or null", "notes": "brief explanation"}}

Only output the JSON."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 3
            }],
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                result_text += block.text
        
        try:
            json_match = re.search(r'\{[^}]+\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    'action': result.get('action', 'remove'),
                    'url': result.get('url'),
                    'notes': result.get('notes', 'No explanation provided.')
                }
        except json.JSONDecodeError:
            pass
        
        return {'action': 'remove', 'url': None, 'notes': result_text[:150] if result_text else 'Could not parse response.'}
        
    except Exception as e:
        return {'action': 'remove', 'url': None, 'notes': f'Error: {str(e)[:100]}'}


# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_nav():
    """Render top navigation bar"""
    st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0; border-bottom: 1px solid #99f6e4; margin-bottom: 1.5rem;">
        <div style="font-size: 1.5rem; font-weight: 700; color: #0d9488;">🔧 Screaming Fixes</div>
        <div style="display: flex; gap: 2rem;">
            <a href="#" style="color: #0d9488; text-decoration: none; font-weight: 500; font-size: 0.95rem;">Home</a>
            <a href="#about" style="color: #64748b; text-decoration: none; font-weight: 500; font-size: 0.95rem;">About</a>
            <a href="#instructions" style="color: #64748b; text-decoration: none; font-weight: 500; font-size: 0.95rem;">Instructions</a>
            <a href="mailto:brett.lindenberg@gmail.com" style="color: #64748b; text-decoration: none; font-weight: 500; font-size: 0.95rem;">Contact</a>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_header():
    """Render the header and introduction"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f0fdfa 0%, #ecfeff 50%, #f0f9ff 100%); 
                padding: 1.75rem 2rem; 
                border-radius: 16px; 
                margin: 0 0 1.5rem 0;
                border: 1px solid #99f6e4;">
        <p style="font-size: 1.15rem; line-height: 1.75; color: #134e4a; margin: 0;">
            <strong style="color: #0d9488;">If you're an SEO or manage WordPress websites, you already use Screaming Frog.</strong><br><br>
            But running audits is the easy part. <em>Actually fixing</em> hundreds of broken links and redirect chains? That's where hours disappear.<br><br>
            <strong style="color: #0d9488;">Work smarter.</strong> Upload your CSV file directly from Screaming Frog, review each broken link, and decide: remove it, replace it, or let AI suggest a fix.<br><br>
            Then the real power kicks in — Screaming Fixes connects to your WordPress site and applies every approved fix automatically. No more logging into each post. No more clicking publish.<br><br>
            This isn't just another audit tool. <strong style="color: #0d9488;">This one actually gets the work done.</strong> Export a CSV or JSON to share your updates with clients.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <h3 style="text-align: center; color: #134e4a; font-weight: 600; margin-bottom: 1.25rem; font-size: 1.35rem;">
        Four Steps to Thousands of Fixed Links
    </h3>
    <div style="display: flex; justify-content: space-between; gap: 1rem; margin-bottom: 1rem;">
        <div style="flex: 1; text-align: center; padding: 1rem; background: linear-gradient(135deg, #f0fdfa 0%, #ffffff 100%); border-radius: 8px; border: 1px solid #ccfbf1;">
            <div style="font-size: 1.5rem; margin-bottom: 0.25rem;">1️⃣</div>
            <div style="font-weight: 600; color: #134e4a;">Upload</div>
            <div style="font-size: 0.85rem; color: #0d9488;">Screaming Frog CSV</div>
        </div>
        <div style="flex: 1; text-align: center; padding: 1rem; background: linear-gradient(135deg, #f0fdfa 0%, #ffffff 100%); border-radius: 8px; border: 1px solid #ccfbf1;">
            <div style="font-size: 1.5rem; margin-bottom: 0.25rem;">2️⃣</div>
            <div style="font-weight: 600; color: #134e4a;">Review</div>
            <div style="font-size: 0.85rem; color: #0d9488;">Broken Links</div>
        </div>
        <div style="flex: 1; text-align: center; padding: 1rem; background: linear-gradient(135deg, #f0fdfa 0%, #ffffff 100%); border-radius: 8px; border: 1px solid #ccfbf1;">
            <div style="font-size: 1.5rem; margin-bottom: 0.25rem;">3️⃣</div>
            <div style="font-weight: 600; color: #134e4a;">Approve</div>
            <div style="font-size: 0.85rem; color: #0d9488;">Remove or Replace</div>
        </div>
        <div style="flex: 1; text-align: center; padding: 1rem; background: linear-gradient(135deg, #f0fdfa 0%, #ffffff 100%); border-radius: 8px; border: 1px solid #ccfbf1;">
            <div style="font-size: 1.5rem; margin-bottom: 0.25rem;">4️⃣</div>
            <div style="font-weight: 600; color: #134e4a;">Apply</div>
            <div style="font-size: 0.85rem; color: #0d9488;">Fix and Export</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("New here? Check the [Instructions](#instructions) section below for setup help.")


def render_upload_section():
    """Render the CSV upload section - unified for both report types"""
    st.markdown('<p class="section-header">Upload CSV</p>', unsafe_allow_html=True)
    
    # Export instructions
    st.markdown("""
    **Upload your Screaming Frog export to get started:**
    """)
    
    with st.expander("📋 Supported Report Types", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **🔗 Broken Links**
            - **Export:** Bulk Export → Response Codes → Client Error (4xx) → Inlinks
            - **Fixes:** Remove broken links or replace with working URLs
            """)
        with col2:
            st.markdown("""
            **🔄 Redirect Chains**
            - **Export:** Reports → Redirects → All Redirects
            - **Fixes:** Update old URLs to their final destinations
            """)
    
    uploaded = st.file_uploader(
        "Upload your Screaming Frog CSV",
        type=['csv'],
        label_visibility='collapsed',
        help="We'll auto-detect whether this is a Broken Links or Redirect Chains export"
    )
    
    st.markdown("""
    <div class="privacy-notice">
        🔒 <strong>Your data is safe</strong> — processed in your browser session only. Nothing is saved to any database. All data is cleared when you close the tab.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="font-size: 0.8rem; color: #64748b; padding: 0.75rem; background: #f8fafc; border-radius: 8px; margin-bottom: 1rem;">
        <strong>Disclaimer:</strong> You are responsible for reviewing and approving all changes before they are applied to your site. 
        Screaming Frog data may occasionally contain errors or false positives. Always verify fixes are appropriate for your specific situation.
    </div>
    """, unsafe_allow_html=True)
    
    if uploaded:
        # First, detect the CSV type
        df_preview = pd.read_csv(uploaded)
        uploaded.seek(0)  # Reset file pointer
        
        csv_type = detect_csv_type(df_preview)
        
        if csv_type == 'redirect_chains':
            # Process as redirect chains
            df = parse_redirect_chains_csv(uploaded)
            if df is not None and len(df) > 0:
                domain = detect_domain(df['Source'].tolist())
                redirects, sitewide, loops = group_redirect_chains(df, domain)
                
                # Initialize decisions for each redirect
                decisions = {}
                for key in redirects:
                    decisions[key] = {
                        'approved_action': '',  # 'replace' or ''
                        'approved_fix': '',  # Will be the final_address
                    }
                
                # Store in session state
                st.session_state.rc_df = df
                st.session_state.rc_domain = domain
                st.session_state.rc_redirects = redirects
                st.session_state.rc_decisions = decisions
                st.session_state.rc_sitewide = sitewide
                st.session_state.rc_loops = loops
                st.session_state.task_type = 'redirect_chains'
                st.session_state.current_task = 'redirect_chains'
                
                # Count unique source pages
                source_pages_count = df['Source'].nunique()
                st.session_state.source_pages_count = source_pages_count
                
                # Check if CSV has post_id column with valid data
                has_post_ids = df['post_id'].notna().any()
                st.session_state.has_post_ids = has_post_ids
                
                # Pre-populate post_id cache from CSV
                if has_post_ids:
                    for _, row in df.iterrows():
                        if pd.notna(row.get('post_id')):
                            st.session_state.post_id_cache[row['Source']] = int(row['post_id'])
                
                # Count stats
                total_redirects = len(redirects)
                temp_count = sum(1 for r in redirects.values() if r['is_temp_redirect'])
                
                # Track upload
                track_event("csv_upload", {
                    "type": "redirect_chains",
                    "unique_redirects": total_redirects,
                    "total_references": len(df),
                    "source_pages": source_pages_count,
                    "sitewide_count": len(sitewide),
                    "loop_count": len(loops),
                    "temp_redirect_count": temp_count
                })
                
                st.success(f"✅ **Redirect Chains detected!** Found **{total_redirects} unique redirects** across {source_pages_count} pages on {domain}")
                
                if sitewide:
                    st.info(f"ℹ️ {len(sitewide)} sitewide links detected (header/footer/sidebar) — shown separately")
                if loops:
                    st.warning(f"⚠️ {len(loops)} redirect loops detected — cannot auto-fix")
                
                st.rerun()
        
        else:
            # Process as broken links (existing logic)
            df = parse_csv(uploaded)
            if df is not None and len(df) > 0:
                domain = detect_domain(df['Source'].tolist())
                broken_urls = group_by_broken_url(df, domain)
                
                decisions = {}
                for url in broken_urls:
                    decisions[url] = {
                        'manual_fix': '',
                        'ai_suggestion': '',
                        'ai_action': '',
                        'ai_notes': '',
                        'approved_fix': '',
                        'approved_action': '',
                    }
                
                st.session_state.df = df
                st.session_state.domain = domain
                st.session_state.broken_urls = broken_urls
                st.session_state.decisions = decisions
                st.session_state.task_type = 'broken_links'
                st.session_state.current_task = 'broken_links'
                
                # Track CSV upload (no PII - just counts)
                track_event("csv_upload", {
                    "type": "broken_links",
                    "unique_broken_urls": len(broken_urls),
                    "total_references": len(df),
                    "source_pages": df['Source'].nunique()
                })
                
                # Count unique source pages
                source_pages_count = df['Source'].nunique()
                st.session_state.source_pages_count = source_pages_count
                
                # Check if CSV has post_id column with valid data
                has_post_ids = df['post_id'].notna().any()
                st.session_state.has_post_ids = has_post_ids
                
                # Pre-populate post_id cache from CSV
                if has_post_ids:
                    for _, row in df.iterrows():
                        if pd.notna(row.get('post_id')):
                            st.session_state.post_id_cache[row['Source']] = int(row['post_id'])
                
                st.success(f"✅ **Broken Links detected!** Found **{len(broken_urls)} unique broken URLs** across {source_pages_count} pages on {domain}")
                st.rerun()


def render_post_id_extraction_guide():
    """Render detailed Screaming Frog Post ID extraction instructions"""
    st.markdown("""
    **One-time setup in Screaming Frog (do this once, use forever):**
    
    Most WordPress sites include a "shortlink" in the HTML that contains the Post ID. 
    We'll configure Screaming Frog to extract it automatically during every crawl.
    
    ---
    
    **Step 1: Open Custom Extraction**
    - In Screaming Frog, go to **Configuration → Custom → Extraction**
    
    **Step 2: Add a new extractor**
    - Click **Add**
    - Set the name to: `post_id`
    - Change the dropdown from "XPath" to **Regex**
    
    **Step 3: Enter the regex pattern**
    ```
    <link[^>]+rel=['"]shortlink['"][^>]+href=['"][^'"]*\\?p=(\\d+)
    ```
    
    **Step 4: Configure extraction settings**
    - Make sure "Extract HTML" is selected (not "Extract Text")
    - Click **OK** to save
    
    **Step 5: Save as default (optional but recommended)**
    - Go to **File → Configuration → Save As Default**
    - Now every future crawl will include Post IDs automatically!
    
    ---
    
    **Step 6: Run your crawl and export**
    - Start a new crawl (or re-crawl your site)
    - After completion, you'll see a **Custom Extraction** tab with Post IDs
    - Export via **Bulk Export → Response Codes → Client Error (4xx) → Inlinks**
    - The `post_id` column will be included automatically
    
    ---
    
    **Troubleshooting:**
    - **No Post IDs found?** Your theme may not include shortlinks. Try this alternative regex for body class:
      ```
      class=['"][^'"]*(?:postid|page-id)-(\\d+)
      ```
    - **Still not working?** Use Agent Mode for up to 25 pages, or manually add a `post_id` column to your CSV.
    """)


def render_mode_selector():
    """Render mode selector after CSV upload"""
    if st.session_state.df is None:
        return
    
    source_pages = st.session_state.source_pages_count
    has_post_ids = st.session_state.has_post_ids
    post_id_count = len(st.session_state.post_id_cache)
    
    st.markdown("### Select Mode")
    st.caption("Both options are **100% free** — choose what fits your workflow.")
    
    # Mode selector cards
    col1, col2 = st.columns(2)
    
    with col1:
        agent_selected = st.session_state.selected_mode == 'agent'
        agent_border = "2px solid #0d9488" if agent_selected else "1px solid #e2e8f0"
        agent_bg = "linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 100%)" if agent_selected else "white"
        
        # Agent mode limits
        if source_pages <= AGENT_MODE_LIMIT:
            agent_status = f"✅ {source_pages} pages — ready to go!"
            agent_status_color = "#059669"
        else:
            agent_status = f"⚠️ {source_pages} pages — will fix first 25 to test (free!)"
            agent_status_color = "#d97706"
        
        st.markdown(f"""
        <div style="background: {agent_bg}; padding: 1.25rem; border-radius: 10px; border: {agent_border}; cursor: pointer; min-height: 150px; display: flex; flex-direction: column;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem;">
                <span style="font-size: 1.25rem;">🤖</span>
                <span style="font-weight: 600; color: #134e4a; font-size: 1.1rem;">Agent Mode</span>
                <span style="background: #14b8a6; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600;">DEFAULT</span>
            </div>
            <div style="font-size: 0.9rem; color: #334155; margin-bottom: 0.75rem; flex-grow: 1;">
                Start fixing immediately. We auto-discover Post IDs by visiting each page. <strong>Perfect for testing. 100% free.</strong>
            </div>
            <div style="font-size: 0.85rem; color: {agent_status_color}; font-weight: 500; min-height: 1.5rem;">{agent_status}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Select Agent Mode", key="select_agent", use_container_width=True, 
                     type="primary" if agent_selected else "secondary"):
            st.session_state.selected_mode = 'agent'
            st.rerun()
    
    with col2:
        enterprise_selected = st.session_state.selected_mode == 'enterprise'
        enterprise_border = "2px solid #0d9488" if enterprise_selected else "1px solid #e2e8f0"
        enterprise_bg = "linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 100%)" if enterprise_selected else "white"
        
        # Enterprise mode status
        if has_post_ids:
            enterprise_status = f"✅ {post_id_count} Post IDs detected — ready!"
            enterprise_status_color = "#059669"
            enterprise_available = True
        else:
            enterprise_status = "⚙️ Requires Post IDs in CSV (2 min setup)"
            enterprise_status_color = "#64748b"
            enterprise_available = False
        
        st.markdown(f"""
        <div style="background: {enterprise_bg}; padding: 1.25rem; border-radius: 10px; border: {enterprise_border}; cursor: pointer; min-height: 150px; display: flex; flex-direction: column;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem;">
                <span style="font-size: 1.25rem;">🚀</span>
                <span style="font-weight: 600; color: #134e4a; font-size: 1.1rem;">Enterprise Mode</span>
            </div>
            <div style="font-size: 0.9rem; color: #334155; margin-bottom: 0.75rem; flex-grow: 1;">
                Unlimited pages, fastest execution. <strong>Best for large sites. 100% free.</strong>
            </div>
            <div style="font-size: 0.85rem; color: {enterprise_status_color}; font-weight: 500; min-height: 1.5rem;">{enterprise_status}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Select Enterprise Mode", key="select_enterprise", use_container_width=True,
                     type="primary" if enterprise_selected else "secondary"):
            st.session_state.selected_mode = 'enterprise'
            st.rerun()
    
    # Show setup instructions if Enterprise selected but no Post IDs
    if st.session_state.selected_mode == 'enterprise' and not has_post_ids:
        st.markdown("---")
        st.markdown("""
        <div style="background: #fef3c7; padding: 1.25rem; border-radius: 10px; border: 1px solid #fcd34d;">
            <div style="font-weight: 600; color: #92400e; margin-bottom: 0.75rem;">⚠️ Enterprise Mode requires Post IDs in your CSV</div>
            <div style="color: #a16207; font-size: 0.95rem; line-height: 1.6;">
                <strong>Why?</strong> WordPress requires Post IDs to identify which content to update — it's how WP understands your unique URLs. 
                But by default, Screaming Frog doesn't include Post IDs in the crawl.<br><br>
                <strong>Solution:</strong> Set up a custom extraction in Screaming Frog to capture Post IDs, then re-crawl and re-upload your CSV. 
                This entire process only takes a few minutes to set up, and you only need to do it once.
            </div>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("📋 How to set up Enterprise Mode (2 min)", expanded=True):
            render_post_id_extraction_guide()


def render_metrics():
    """Render summary metrics"""
    broken_urls = st.session_state.broken_urls
    decisions = st.session_state.decisions
    
    total = len(broken_urls)
    internal = sum(1 for info in broken_urls.values() if info['is_internal'])
    external = total - internal
    approved = sum(1 for d in decisions.values() if d['approved_action'])
    pending = total - approved
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Broken", total)
    with col2:
        st.metric("Internal", internal)
    with col3:
        st.metric("External", external)
    with col4:
        st.metric("✅ Approved", approved)


def render_spreadsheet():
    """Render the main spreadsheet view"""
    broken_urls = st.session_state.broken_urls
    decisions = st.session_state.decisions
    domain = st.session_state.domain
    
    # User guidance
    with st.expander("📖 How to use this tool", expanded=False):
        st.markdown("""
        **Review each broken URL and choose an action:**
        
        1. **Click on a URL row** to expand it and see your options
        2. **Check the URL** — click the link to verify it's actually broken (Screaming Frog sometimes has false positives)
        3. **Choose an action:**
           - **🗑️ Remove Link** — Deletes the link but keeps the anchor text visible on your page
           - **✓ Use Manual** — Enter a replacement URL yourself, then click to approve
           - **✓ Use AI** — Get an AI suggestion (requires API key), then approve if correct
           - **⏭️ Ignore** — Mark as reviewed but take no action (for false positives)
        
        4. **Export or Apply** — Once you've approved your fixes, scroll down to export as CSV/JSON or apply directly to WordPress
        
        💡 **Tip:** Each broken URL may appear on multiple pages. Fix it once here, and it applies everywhere.
        """)
    
    # Filters
    st.markdown("**Filters:**")
    filter_cols = st.columns(4)
    with filter_cols[0]:
        st.session_state.filter_internal = st.checkbox("Internal", value=True)
    with filter_cols[1]:
        st.session_state.filter_external = st.checkbox("External", value=True)
    with filter_cols[2]:
        st.session_state.show_pending = st.checkbox("Pending", value=True)
    with filter_cols[3]:
        st.session_state.show_approved = st.checkbox("Approved", value=True)
    
    # Count pending URLs for bulk actions
    pending_urls = [url for url, d in decisions.items() if not d['approved_action']]
    pending_internal = [url for url in pending_urls if broken_urls[url]['is_internal']]
    pending_external = [url for url in pending_urls if not broken_urls[url]['is_internal']]
    
    # Bulk actions
    if pending_urls:
        with st.expander(f"⚡ Bulk Actions ({len(pending_urls)} pending)", expanded=False):
            st.markdown("Apply the same action to multiple URLs at once:")
            
            bulk_cols = st.columns(3)
            
            with bulk_cols[0]:
                if st.button(f"🗑️ Remove All Pending ({len(pending_urls)})", use_container_width=True):
                    st.session_state.bulk_action = 'remove_all'
                    
            with bulk_cols[1]:
                if st.button(f"🗑️ Remove Internal ({len(pending_internal)})", use_container_width=True, disabled=len(pending_internal) == 0):
                    st.session_state.bulk_action = 'remove_internal'
                    
            with bulk_cols[2]:
                if st.button(f"⏭️ Ignore External ({len(pending_external)})", use_container_width=True, disabled=len(pending_external) == 0):
                    st.session_state.bulk_action = 'ignore_external'
            
            # Handle bulk action confirmation
            if st.session_state.get('bulk_action'):
                action = st.session_state.bulk_action
                
                if action == 'remove_all':
                    st.warning(f"⚠️ This will mark **{len(pending_urls)} URLs** for link removal.")
                    target_urls = pending_urls
                    action_type = 'remove'
                elif action == 'remove_internal':
                    st.warning(f"⚠️ This will mark **{len(pending_internal)} internal URLs** for link removal.")
                    target_urls = pending_internal
                    action_type = 'remove'
                elif action == 'ignore_external':
                    st.warning(f"⚠️ This will mark **{len(pending_external)} external URLs** as ignored.")
                    target_urls = pending_external
                    action_type = 'ignore'
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Confirm", type="primary", use_container_width=True):
                        for url in target_urls:
                            st.session_state.decisions[url]['approved_action'] = action_type
                            st.session_state.decisions[url]['approved_fix'] = ''
                        st.session_state.bulk_action = None
                        st.toast(f"✅ Applied to {len(target_urls)} URLs", icon="✅")
                        time.sleep(0.5)
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.session_state.bulk_action = None
                        st.rerun()
    
    # Apply filters
    filtered_urls = []
    for url, info in broken_urls.items():
        if info['is_internal'] and not st.session_state.filter_internal:
            continue
        if not info['is_internal'] and not st.session_state.filter_external:
            continue
        
        has_approval = bool(decisions[url]['approved_action'])
        if has_approval and not st.session_state.show_approved:
            continue
        if not has_approval and not st.session_state.show_pending:
            continue
        
        filtered_urls.append(url)
    
    if not filtered_urls:
        st.info("No URLs match your filters")
        return
    
    # Sort options
    sort_col1, sort_col2 = st.columns([1, 3])
    with sort_col1:
        sort_option = st.selectbox(
            "Sort by:",
            ["Impact (pages affected)", "Status Code", "Internal First", "External First"],
            index=["impact", "status_code", "internal_first", "external_first"].index(st.session_state.sort_by) if st.session_state.sort_by in ["impact", "status_code", "internal_first", "external_first"] else 0,
            key="sort_selector"
        )
        # Map display to value
        sort_map = {
            "Impact (pages affected)": "impact",
            "Status Code": "status_code",
            "Internal First": "internal_first",
            "External First": "external_first"
        }
        st.session_state.sort_by = sort_map[sort_option]
    
    # Apply sorting
    if st.session_state.sort_by == "impact":
        filtered_urls.sort(key=lambda u: broken_urls[u]['count'], reverse=True)
    elif st.session_state.sort_by == "status_code":
        filtered_urls.sort(key=lambda u: broken_urls[u]['status_code'])
    elif st.session_state.sort_by == "internal_first":
        filtered_urls.sort(key=lambda u: (0 if broken_urls[u]['is_internal'] else 1, -broken_urls[u]['count']))
    elif st.session_state.sort_by == "external_first":
        filtered_urls.sort(key=lambda u: (1 if broken_urls[u]['is_internal'] else 0, -broken_urls[u]['count']))
    
    # Pagination
    total = len(filtered_urls)
    per_page = st.session_state.per_page
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(st.session_state.page, total_pages - 1)
    
    start = page * per_page
    end = min(start + per_page, total)
    page_urls = filtered_urls[start:end]
    
    st.markdown(f"**Showing {start+1}-{end} of {total} broken URLs**")
    
    # Check if user has made any fixes yet (to show/hide first-row hint)
    has_any_fixes = any(d['approved_action'] for d in decisions.values())
    is_on_first_page = page == 0
    
    # Render each URL
    for idx, url in enumerate(page_urls):
        # Show hint only on first row of first page, before any fixes made
        is_first_row = (idx == 0 and is_on_first_page and not has_any_fixes)
        render_url_row(url, broken_urls[url], decisions[url], domain, is_first_row)
    
    # Pagination
    if total_pages > 1:
        pcol1, pcol2, pcol3 = st.columns([1, 2, 1])
        with pcol1:
            if st.button("← Previous", disabled=page == 0, key="prev"):
                st.session_state.page = page - 1
                st.rerun()
        with pcol2:
            st.markdown(f"<div style='text-align:center; padding-top: 0.5rem;'>Page {page+1} of {total_pages}</div>", unsafe_allow_html=True)
        with pcol3:
            if st.button("Next →", disabled=page >= total_pages - 1, key="next"):
                st.session_state.page = page + 1
                st.rerun()


def render_url_row(url: str, info: Dict, decision: Dict, domain: str, is_first_row: bool = False):
    """Render a single URL row"""
    
    # Status badge
    badge_class = 'status-4xx'
    type_class = 'status-internal' if info['is_internal'] else 'status-external'
    type_label = 'Internal' if info['is_internal'] else 'External'
    
    # Approval status badge with fix preview
    fix_preview = ""
    if decision['approved_action'] == 'ignore':
        status_badge = '<span class="ignored-badge">⏭️ Ignored</span>'
    elif decision['approved_action'] == 'remove':
        status_badge = '<span class="approved-badge">✓ Remove Link</span>'
    elif decision['approved_action'] == 'replace':
        status_badge = '<span class="approved-badge">✓ Replace URL</span>'
        # Show replacement URL preview
        replacement = decision['approved_fix']
        if replacement:
            short_url = replacement[:40] + '...' if len(replacement) > 40 else replacement
            fix_preview = f'<div style="font-size: 0.75rem; color: #059669; margin-top: 0.25rem;">→ {short_url}</div>'
    elif decision['approved_action']:
        status_badge = f'<span class="approved-badge">✓ {decision["approved_action"].upper()}</span>'
    else:
        status_badge = '<span class="pending-badge">⏳ Pending</span>'
    
    # Anchors preview
    anchor_preview = ""
    if info['anchors']:
        anchor_preview = f'<span class="anchor-preview">"{info["anchors"][0][:30]}{"..." if len(info["anchors"][0]) > 30 else ""}"</span>'
    
    st.markdown(f"""
    <div class="url-row">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
            <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">
                <span style="font-size: 0.8rem; color: #64748b;">Status Code:</span>
                <span class="status-badge {badge_class}">{info['status_code']}</span>
                <span style="font-size: 0.8rem; color: #64748b;">Link Type:</span>
                <span class="status-badge {type_class}">{type_label}</span>
                <span style="font-size: 0.8rem; color: #64748b;">Action:</span>
                {status_badge}
            </div>
            <div style="color: #64748b; font-size: 0.8rem;">Affects {info['count']} page(s)</div>
        </div>
        <div class="url-text"><a href="{url}" target="_blank" rel="noopener noreferrer" style="color: #134e4a; text-decoration: none; border-bottom: 1px dashed #99f6e4;">{url}</a> <span style="font-size: 0.7rem; color: #64748b;">↗</span></div>
        {f'<div style="margin-top: 0.25rem;">{anchor_preview}</div>' if anchor_preview else ''}
        {fix_preview}
    </div>
    """, unsafe_allow_html=True)
    
    # Show first-row hint if applicable
    if is_first_row and st.session_state.editing_url is None:
        st.markdown("""
        <div style="color: #0d9488; font-size: 0.9rem; font-weight: 500; margin-bottom: 0.25rem;">
            👇 Start here — click to set your first fix
        </div>
        """, unsafe_allow_html=True)
    
    # Action area - use button to toggle inline editing
    is_editing = st.session_state.editing_url == url
    
    col1, col2 = st.columns([1, 5])
    with col1:
        if is_editing:
            if st.button("❌ Close", key=f"close_{url}", use_container_width=True):
                st.session_state.editing_url = None
                st.rerun()
        else:
            if st.button("📝 Set Fix", key=f"edit_{url}", use_container_width=True):
                st.session_state.editing_url = url
                st.rerun()
    
    # Show inline edit form if this URL is being edited
    if is_editing:
        st.markdown("""
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem; margin-top: 0.5rem;">
        """, unsafe_allow_html=True)
        
        st.markdown("**Choose a fix for this broken link:**")
        
        # Horizontal radio selection
        fix_options = ["🗑️ Remove Link", "✏️ Use Manual", "🤖 Use AI", "⏭️ Ignore"]
        
        # Determine default selection based on current state
        if decision['approved_action'] == 'remove':
            default_idx = 0
        elif decision['approved_action'] == 'replace':
            default_idx = 1
        elif decision['approved_action'] == 'ignore':
            default_idx = 3
        else:
            default_idx = 0
        
        selected_fix = st.radio(
            "Fix type",
            fix_options,
            index=default_idx,
            horizontal=True,
            key=f"fix_type_{url}",
            label_visibility='collapsed'
        )
        
        st.markdown("---")
        
        # Show content based on selection
        if selected_fix == "🗑️ Remove Link":
            st.markdown("""
            **What this does:**  
            Removes the `<a>` hyperlink tag but **keeps the anchor text visible** on your page. 
            
            For example: `<a href="broken.com">Click here</a>` becomes just `Click here`
            
            ✅ **Use when:** The destination page no longer exists and there's no suitable replacement.
            """)
            
            if st.button("💾 Save Selection", key=f"save_remove_{url}", type="primary", use_container_width=True):
                st.session_state.decisions[url]['approved_action'] = 'remove'
                st.session_state.decisions[url]['approved_fix'] = ''
                st.session_state.editing_url = None  # Close the form
                st.toast("✅ Saved: Remove Link", icon="✅")
                time.sleep(0.3)
                st.rerun()
        
        elif selected_fix == "✏️ Use Manual":
            st.markdown("""
            **What this does:**  
            Replaces the broken URL with a new URL you provide. The anchor text stays the same.
            
            ✅ **Use when:** You know the correct replacement URL (e.g., content moved to a new location).
            """)
            
            manual_fix = st.text_input(
                "Enter replacement URL:",
                value=decision['manual_fix'],
                placeholder="https://example.com/new-page",
                key=f"manual_{url}"
            )
            
            if manual_fix != decision['manual_fix']:
                st.session_state.decisions[url]['manual_fix'] = manual_fix
            
            if manual_fix:
                if st.button("💾 Save Selection", key=f"save_manual_{url}", type="primary", use_container_width=True):
                    st.session_state.decisions[url]['approved_action'] = 'replace'
                    st.session_state.decisions[url]['approved_fix'] = manual_fix
                    st.session_state.editing_url = None  # Close the form
                    st.toast("✅ Saved: Replace URL", icon="✅")
                    time.sleep(0.3)
                    st.rerun()
            else:
                st.caption("⬆️ Enter a replacement URL above to save")
        
        elif selected_fix == "🤖 Use AI":
            # Get mode and remaining suggestions
            selected_mode = st.session_state.get('selected_mode', 'agent')
            remaining = st.session_state.ai_suggestions_remaining
            user_has_key = bool(st.session_state.anthropic_key)
            
            st.markdown("""
            **What this does:**  
            AI searches the web to find a suitable replacement URL or recommends removal if no replacement exists.
            """)
            
            # Show free suggestions counter for Agent Mode
            if selected_mode == 'agent' and AGENT_MODE_API_KEY:
                if remaining > 0:
                    st.markdown(f"🎁 **{remaining} of {AGENT_MODE_FREE_SUGGESTIONS} free AI suggestions available**")
                elif not user_has_key:
                    st.markdown("🎁 **0 of 5 free AI suggestions remaining**")
            
            st.markdown("✅ **Use when:** You want help finding where content may have moved.")
            
            # Show existing AI suggestion if available
            if decision['ai_action']:
                st.markdown("---")
                st.markdown("**AI Recommendation:**")
                if decision['ai_action'] == 'replace':
                    st.success(f"Replace with: `{decision['ai_suggestion']}`")
                else:
                    st.info("🗑️ Remove this link (keep anchor text)")
                
                if decision['ai_notes']:
                    st.markdown(f"**Why:** {decision['ai_notes']}")
                
                if st.button("💾 Accept AI Suggestion", key=f"save_ai_{url}", type="primary", use_container_width=True):
                    st.session_state.decisions[url]['approved_action'] = decision['ai_action']
                    st.session_state.decisions[url]['approved_fix'] = decision['ai_suggestion']
                    st.session_state.editing_url = None  # Close the form
                    action_label = "Replace URL" if decision['ai_action'] == 'replace' else "Remove Link"
                    st.toast(f"✅ Saved: {action_label}", icon="✅")
                    time.sleep(0.3)
                    st.rerun()
            else:
                # No AI suggestion yet - show button based on mode
                st.markdown("---")
                
                if selected_mode == 'agent':
                    # Agent Mode - use free suggestions or user's key
                    if remaining > 0 and AGENT_MODE_API_KEY:
                        # Free suggestions available
                        if st.button("🔍 Get AI Suggestion", key=f"ai_{url}", use_container_width=True):
                            with st.spinner("AI is searching for alternatives..."):
                                result = get_ai_suggestion(url, info, domain, AGENT_MODE_API_KEY)
                                st.session_state.decisions[url]['ai_action'] = result['action']
                                st.session_state.decisions[url]['ai_suggestion'] = result['url'] or ''
                                st.session_state.decisions[url]['ai_notes'] = result['notes']
                                st.session_state.ai_suggestions_remaining -= 1
                                st.rerun()
                    elif user_has_key:
                        # User entered their own key
                        st.success("✅ Using your API key — unlimited suggestions")
                        if st.button("🔍 Get AI Suggestion", key=f"ai_{url}", use_container_width=True):
                            with st.spinner("AI is searching for alternatives..."):
                                result = get_ai_suggestion(url, info, domain, st.session_state.anthropic_key)
                                st.session_state.decisions[url]['ai_action'] = result['action']
                                st.session_state.decisions[url]['ai_suggestion'] = result['url'] or ''
                                st.session_state.decisions[url]['ai_notes'] = result['notes']
                                st.rerun()
                    else:
                        # Free suggestions exhausted, no user key
                        st.markdown("""
                        <div style="background: #fef3c7; padding: 1rem; border-radius: 8px; border: 1px solid #fcd34d; margin-bottom: 1rem;">
                            <div style="font-weight: 600; color: #92400e; margin-bottom: 0.5rem;">🎁 You've used all 5 free AI suggestions!</div>
                            <div style="color: #a16207; font-size: 0.9rem;">
                                Enter your own Claude API key for unlimited suggestions, or continue with manual fixes.
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        api_key_input = st.text_input(
                            "Your Claude API Key:",
                            type="password",
                            placeholder="sk-ant-...",
                            key=f"api_key_{url}",
                        )
                        if api_key_input:
                            st.session_state.anthropic_key = api_key_input
                            st.success("✅ API key saved!")
                            st.rerun()
                        
                        st.caption("Get your key at [console.anthropic.com](https://console.anthropic.com) • Keys are stored in your browser session only")
                
                else:
                    # Enterprise Mode - require user's key
                    if user_has_key:
                        if st.button("🔍 Get AI Suggestion", key=f"ai_{url}", use_container_width=True):
                            with st.spinner("AI is searching for alternatives..."):
                                result = get_ai_suggestion(url, info, domain, st.session_state.anthropic_key)
                                st.session_state.decisions[url]['ai_action'] = result['action']
                                st.session_state.decisions[url]['ai_suggestion'] = result['url'] or ''
                                st.session_state.decisions[url]['ai_notes'] = result['notes']
                                st.rerun()
                    else:
                        st.info("🔑 **Enterprise Mode:** Enter your Claude API key for AI suggestions")
                        
                        api_key_input = st.text_input(
                            "Your Claude API Key:",
                            type="password",
                            placeholder="sk-ant-...",
                            key=f"api_key_{url}",
                        )
                        if api_key_input:
                            st.session_state.anthropic_key = api_key_input
                            st.success("✅ API key saved!")
                            st.rerun()
                        
                        st.caption("Get your key at [console.anthropic.com](https://console.anthropic.com) • Keys are stored in your browser session only")
        
        elif selected_fix == "⏭️ Ignore":
            st.markdown("""
            **What this does:**  
            Marks this URL as **reviewed but takes no action**. The link remains unchanged on your site.
            
            ✅ **Use when:** 
            - It's a false positive (the link actually works)
            - You'll handle it manually outside this tool
            - You want to skip it for now but track that you've seen it
            """)
            
            if st.button("💾 Save Selection", key=f"save_ignore_{url}", type="primary", use_container_width=True):
                st.session_state.decisions[url]['approved_action'] = 'ignore'
                st.session_state.decisions[url]['approved_fix'] = ''
                st.session_state.editing_url = None  # Close the form
                st.toast("✅ Saved: Ignored", icon="✅")
                time.sleep(0.3)
                st.rerun()
        
        # Clear/Reset option if already has an action
        if decision['approved_action']:
            st.markdown("---")
            if st.button("↩️ Clear Selection (Reset to Pending)", key=f"clear_{url}", use_container_width=True):
                st.session_state.decisions[url]['approved_action'] = ''
                st.session_state.decisions[url]['approved_fix'] = ''
                st.session_state.editing_url = None  # Close the form
                st.toast("↩️ Reset to Pending", icon="↩️")
                time.sleep(0.3)
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)


def render_wordpress_section():
    """Render WordPress connection section"""
    st.markdown('<p class="section-header">WordPress Connection</p>', unsafe_allow_html=True)
    
    st.markdown("**Required to publish updates directly to your site.**")
    
    st.markdown("""
    <div class="privacy-notice">
        🔒 <strong>Your credentials are safe</strong> — stored in your browser session only. Nothing is saved to any database. All data is cleared when you close the tab.
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.wp_connected:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success("✅ Connected to WordPress")
        with col2:
            if st.button("Disconnect"):
                if st.session_state.wp_client:
                    st.session_state.wp_client.close()
                st.session_state.wp_connected = False
                st.session_state.wp_client = None
                st.rerun()
    else:
        st.markdown("Connect to apply fixes directly to your WordPress site via the REST API.")
        
        # Setup instructions dropdown
        with st.expander("📋 **How to get your Application Password** (required)", expanded=False):
            st.markdown("""
            WordPress Application Passwords let external tools like Screaming Fixes access your site securely. 
            **You'll need a WordPress account with Administrator privileges.**
            
            ---
            
            **Step 1:** Log into your WordPress Admin dashboard
            
            **Step 2:** Go to **Users → Profile** (or click your name in the top-right corner)
            
            **Step 3:** Scroll down to the **Application Passwords** section
            
            **Step 4:** In the "New Application Password Name" field, enter: `Screaming Fixes`
            
            **Step 5:** Click **Add New Application Password**
            
            **Step 6:** Copy the generated password (it looks like `xxxx xxxx xxxx xxxx xxxx xxxx`)
            - ⚠️ **Important:** You'll only see this password once! Copy it now.
            - The spaces in the password are fine — paste it exactly as shown.
            
            ---
            
            **Troubleshooting:**
            - **Don't see Application Passwords?** You need WordPress 5.6 or higher, or install the [Application Passwords plugin](https://wordpress.org/plugins/application-passwords/).
            - **Getting 401 errors?** Make sure your username is correct and you're using an Application Password (not your regular login password).
            - **Getting 403 errors?** Your user account may not have permission to edit posts. Ask a site admin for help.
            """)
        
        col1, col2 = st.columns(2)
        with col1:
            site_url = st.text_input(
                "Site URL",
                placeholder="https://your-site.com",
                help="Your WordPress site URL (without /wp-json)"
            )
        with col2:
            username = st.text_input(
                "Username",
                placeholder="admin",
                help="Your WordPress admin username"
            )
        
        app_password = st.text_input(
            "Application Password",
            type="password",
            placeholder="xxxx xxxx xxxx xxxx xxxx xxxx",
            help="The Application Password you generated (not your regular login password)"
        )
        
        if st.button("🔌 Connect to WordPress", type="primary"):
            if not all([site_url, username, app_password]):
                st.error("Please fill in all fields")
            elif not WP_AVAILABLE:
                st.error("WordPress client not available. Check that wordpress_client.py is present.")
            else:
                with st.spinner("Connecting..."):
                    try:
                        client = WordPressClient(site_url, username, app_password)
                        result = client.test_connection()
                        
                        if result["success"]:
                            st.session_state.wp_connected = True
                            st.session_state.wp_client = client
                            st.success(f"✅ {result['message']}")
                            st.rerun()
                        else:
                            st.error(result["message"])
                    except Exception as e:
                        st.error(f"Connection failed: {str(e)}")


def render_export_section():
    """Render export section"""
    decisions = st.session_state.decisions
    broken_urls = st.session_state.broken_urls
    
    approved = [(url, d) for url, d in decisions.items() if d['approved_action'] and d['approved_action'] != 'ignore']
    has_approved = len(approved) > 0
    
    st.markdown('<p class="section-header">Export & Apply</p>', unsafe_allow_html=True)
    
    # Status message based on approved count
    if has_approved:
        st.markdown(f"✅ **{len(approved)} fixes approved** and ready")
    else:
        st.markdown("No fixes approved yet. Approve fixes above to enable export.")
    
    # Export buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export CSV", use_container_width=True, disabled=not has_approved):
            export_data = create_export_data()
            
            # Track export (counts only, no URLs)
            remove_count = sum(1 for d in export_data if d['action'] == 'remove')
            replace_count = sum(1 for d in export_data if d['action'] == 'replace')
            track_event("export", {
                "format": "csv",
                "total_fixes": len(export_data),
                "remove_count": remove_count,
                "replace_count": replace_count
            })
            
            csv_data = pd.DataFrame(export_data).to_csv(index=False)
            st.download_button(
                "Download CSV",
                data=csv_data,
                file_name=f"screaming_fixes_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    with col2:
        if st.button("📥 Export JSON", use_container_width=True, disabled=not has_approved):
            export_data = create_export_data()
            
            # Track export (counts only, no URLs)
            remove_count = sum(1 for d in export_data if d['action'] == 'remove')
            replace_count = sum(1 for d in export_data if d['action'] == 'replace')
            track_event("export", {
                "format": "json",
                "total_fixes": len(export_data),
                "remove_count": remove_count,
                "replace_count": replace_count
            })
            
            json_data = json.dumps(export_data, indent=2)
            st.download_button(
                "Download JSON",
                data=json_data,
                file_name=f"screaming_fixes_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )
    
    # WordPress apply section - only show after connected
    if not st.session_state.wp_connected:
        # Don't show this section until WordPress is connected
        return
    
    st.markdown("---")
    st.markdown("**Apply directly to WordPress:**")
    
    if not has_approved:
        st.info("Approve some fixes above first")
        return
    
    # Count how many source pages need fixes
    source_pages_to_fix = set()
    for url, decision in approved:
        for source in broken_urls[url]['sources']:
            source_pages_to_fix.add(source)
    
    pages_to_fix = len(source_pages_to_fix)
    has_post_ids = st.session_state.has_post_ids
    selected_mode = st.session_state.get('selected_mode', 'agent')
    
    # Check if we have post_ids for all pages
    if has_post_ids:
        pages_with_ids = sum(1 for s in source_pages_to_fix if s in st.session_state.post_id_cache)
        all_have_ids = pages_with_ids == pages_to_fix
    else:
        all_have_ids = False
        pages_with_ids = 0
    
    # Handle based on selected mode
    if selected_mode == 'enterprise':
        # Enterprise Mode selected
        if all_have_ids:
            st.success(f"🚀 **Enterprise Mode:** All {pages_to_fix} pages have Post IDs — ready for maximum speed!")
            render_wordpress_execute_ui(approved, source_pages_to_fix)
        else:
            st.error("🚀 **Enterprise Mode:** Post IDs required but not found in your CSV.")
            st.markdown("**To use Enterprise Mode:**")
            st.markdown("1. Set up Screaming Frog to extract Post IDs (see instructions above)")
            st.markdown("2. Re-crawl your site")
            st.markdown("3. Re-upload your CSV")
            st.markdown("")
            st.info("💡 **Or switch to Agent Mode** to fix up to 25 pages right now!")
    
    else:
        # Agent Mode selected
        if pages_to_fix <= AGENT_MODE_LIMIT:
            # Within limit - can fix all
            st.info(f"🤖 **Agent Mode:** {pages_to_fix} pages to update")
            
            # Sample check if not done
            if not st.session_state.post_id_check_done:
                st.markdown("Before applying, let's verify your site supports automatic Post ID discovery.")
                if st.button("🔍 Run Compatibility Check", use_container_width=True):
                    run_post_id_sample_check(list(source_pages_to_fix)[:3])
            else:
                if st.session_state.post_id_check_passed:
                    st.success("✅ Compatibility check passed! Your site supports automatic Post ID lookup.")
                    render_wordpress_execute_ui(approved, source_pages_to_fix)
                else:
                    st.error("❌ Could not find Post IDs automatically on your site.")
                    st.info("💡 Try setting up Enterprise Mode for more reliable Post ID handling.")
        
        else:
            # Over limit - offer test run
            pages_over = pages_to_fix - AGENT_MODE_LIMIT
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%); padding: 1.25rem; border-radius: 10px; margin-bottom: 1rem; border: 1px solid #7dd3fc;">
                <div style="font-weight: 600; color: #0c4a6e; margin-bottom: 0.5rem;">🤖 Agent Mode: Test Run</div>
                <div style="color: #0369a1; font-size: 0.95rem;">
                    You have {pages_to_fix} pages, but Agent Mode handles {AGENT_MODE_LIMIT} at a time.<br>
                    <strong>Let's fix the first {AGENT_MODE_LIMIT} pages</strong> so you can see the tool in action!
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Select first 25 pages
            test_run_pages = list(source_pages_to_fix)[:AGENT_MODE_LIMIT]
            
            # Filter approved fixes to only those affecting test run pages
            test_run_approved = []
            for url, decision in approved:
                sources_in_test = [s for s in broken_urls[url]['sources'] if s in test_run_pages]
                if sources_in_test:
                    test_run_approved.append((url, decision))
            
            st.markdown(f"**Test run:** {len(test_run_approved)} broken URLs across {len(test_run_pages)} pages")
            
            # Sample check if not done
            if not st.session_state.post_id_check_done:
                if st.button("🔍 Run Compatibility Check", use_container_width=True, key="test_run_check"):
                    run_post_id_sample_check(test_run_pages[:3])
            else:
                if st.session_state.post_id_check_passed:
                    st.success("✅ Compatibility check passed!")
                    render_wordpress_execute_ui(test_run_approved, set(test_run_pages), is_test_run=True)
                else:
                    st.error("❌ Automatic Post ID lookup failed.")
                    st.info("💡 Try setting up Enterprise Mode for more reliable Post ID handling.")


def run_post_id_sample_check(sample_urls: List[str]):
    """Run sample check on a few URLs to verify Post ID discovery works"""
    client = st.session_state.wp_client
    
    with st.status("Checking compatibility...", expanded=True) as status:
        found = 0
        failed = 0
        
        for url in sample_urls:
            st.write(f"Testing: `{url[:60]}...`")
            post_id = client.find_post_id_by_url(url)
            
            if post_id:
                st.write(f"  ✅ Found Post ID: {post_id}")
                found += 1
                st.session_state.post_id_cache[url] = post_id
            else:
                st.write(f"  ❌ Post ID not found")
                failed += 1
        
        st.session_state.post_id_check_done = True
        
        # Pass if at least half succeeded
        if found >= len(sample_urls) / 2:
            st.session_state.post_id_check_passed = True
            status.update(label="✅ Compatibility check passed!", state="complete")
        else:
            st.session_state.post_id_check_passed = False
            status.update(label="❌ Compatibility check failed", state="error")
    
    st.rerun()


def render_large_dataset_instructions():
    """Show instructions for handling large datasets"""
    st.markdown("---")
    st.markdown("### 📋 How to Add Post IDs to Your CSV")
    
    with st.expander("**Option 1: Screaming Frog Custom Extraction (Recommended)**", expanded=True):
        st.markdown("""
        Add Post IDs directly during your crawl using Screaming Frog's custom extraction:
        
        **Setup (one-time):**
        1. In Screaming Frog, go to **Configuration → Custom → Extraction**
        2. Click **Add**
        3. Set the name to `post_id`
        4. Change the dropdown from "XPath" to **Regex**
        5. Enter this pattern:
        ```
        <link[^>]+rel=["']shortlink["'][^>]+href=["'][^"']*\\?p=(\\d+)
        ```
        6. Click **OK**
        
        **Run your crawl:**
        1. Start a new crawl of your site
        2. After completion, the Post ID will appear in the **Custom Extraction** tab
        3. Export your data — the `post_id` column will be included
        4. Upload the new CSV here
        
        *Most WordPress sites include a shortlink meta tag with the Post ID.*
        """)
    
    with st.expander("**Option 2: Manual Post ID Lookup**"):
        st.markdown("""
        Find Post IDs manually in WordPress Admin:
        
        1. Go to **WordPress Admin → Posts** (or Pages)
        2. Hover over the post/page title
        3. Look at the URL in your browser status bar: `post.php?post=12345`
        4. The number after `post=` is your Post ID
        
        *Or:* Edit the post/page and check the URL — it contains `post=12345`
        
        Add a `post_id` column to your CSV and re-upload.
        """)
    
    with st.expander("**Option 3: Export & Update Manually**"):
        st.markdown("""
        Export your approved fixes as CSV and apply them manually:
        
        1. Click **Export CSV** above
        2. Open in Excel/Google Sheets
        3. For each row, find the Post ID and apply the fix in WordPress
        
        *This bypasses the API entirely but requires manual work.*
        """)


def render_wordpress_execute_ui(approved: List, source_pages_to_fix: set, is_test_run: bool = False):
    """Render the execute UI when ready to apply fixes"""
    pages_to_fix = len(source_pages_to_fix)
    
    st.markdown("---")
    
    if is_test_run:
        st.markdown(f"""
        <div style="background: #eff6ff; padding: 0.75rem 1rem; border-radius: 8px; border: 1px solid #bfdbfe; margin-bottom: 1rem;">
            <span style="font-weight: 600; color: #1e40af;">🧪 Test Run:</span>
            <span style="color: #3730a3;">Fixing {len(approved)} broken URLs across {pages_to_fix} pages (first {AGENT_MODE_LIMIT} pages only)</span>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        button_label = "🧪 Run Test (25 pages)" if is_test_run else "🚀 Apply Fixes to WordPress"
        if st.button(button_label, type="primary", use_container_width=True):
            run_agent_fixes(approved, source_pages_to_fix, is_test_run)
    
    with col2:
        if st.session_state.get('wp_execute_results'):
            if st.button("📋 View Last Results", use_container_width=True):
                pass  # Results shown below
    
    # Show results if any
    render_wp_results(is_test_run)


def run_agent_fixes(approved: List, source_pages_to_fix: set, is_test_run: bool = False):
    """Run the agent to apply fixes with live view"""
    client = st.session_state.wp_client
    broken_urls = st.session_state.broken_urls
    
    # Build list of all fixes to apply (only for pages in source_pages_to_fix)
    fixes_to_apply = []
    for url, decision in approved:
        info = broken_urls[url]
        for source in info['sources']:
            # Only include if this source is in our target pages
            if source in source_pages_to_fix:
                fixes_to_apply.append({
                    'source_url': source,
                    'broken_url': url,
                    'action': decision['approved_action'],
                    'replacement_url': decision['approved_fix'] if decision['approved_action'] == 'replace' else '',
                    'post_id': st.session_state.post_id_cache.get(source)  # May be None
                })
    
    total_fixes = len(fixes_to_apply)
    results = []
    skipped_for_retry = []
    
    st.markdown("### 🤖 Applying Fixes")
    
    progress_bar = st.progress(0)
    status_container = st.container()
    
    with status_container:
        for i, fix in enumerate(fixes_to_apply):
            progress_bar.progress((i + 1) / total_fixes)
            
            with st.status(f"Fix {i+1} of {total_fixes}", expanded=True) as status:
                # Step 1: Get Post ID
                post_id = fix['post_id']
                
                if not post_id:
                    st.write(f"🔍 Finding Post ID for: `{fix['source_url'][:50]}...`")
                    post_id = client.find_post_id_by_url(fix['source_url'])
                    
                    if post_id:
                        st.write(f"   ✅ Found Post ID: {post_id}")
                        st.session_state.post_id_cache[fix['source_url']] = post_id
                    else:
                        # Check if it's a category/archive/tag page
                        source_lower = fix['source_url'].lower()
                        is_archive = any(x in source_lower for x in ['/category/', '/tag/', '/author/', '/page/', '/archive/'])
                        
                        if is_archive:
                            st.write(f"   ℹ️ This is an archive/category page (dynamically generated)")
                            st.write(f"   💡 Fix the links on individual posts — archive pages will update automatically")
                            msg = 'Archive/category page - fix individual posts instead'
                        else:
                            st.write(f"   ❌ Post ID not found — skipping")
                            msg = 'Post ID not found'
                        
                        results.append({
                            'source_url': fix['source_url'],
                            'broken_url': fix['broken_url'],
                            'action': fix['action'],
                            'status': 'skipped',
                            'message': msg
                        })
                        skipped_for_retry.append(fix)
                        status.update(label=f"⏭️ Skipped", state="error")
                        continue
                else:
                    st.write(f"📄 Post ID: {post_id} (from CSV)")
                
                # Step 2: Apply fix
                st.write(f"🔧 Applying: **{fix['action'].upper()}**")
                st.write(f"   Target: `{fix['broken_url'][:50]}...`")
                
                try:
                    if fix['action'] == 'remove':
                        result = client.remove_link(post_id, fix['broken_url'], dry_run=False)
                    else:
                        result = client.replace_link(post_id, fix['broken_url'], fix['replacement_url'], dry_run=False)
                    
                    if result['success']:
                        st.write(f"   ✅ {result['message']}")
                        results.append({
                            'source_url': fix['source_url'],
                            'broken_url': fix['broken_url'],
                            'action': fix['action'],
                            'status': 'success',
                            'message': result['message']
                        })
                        status.update(label=f"✅ Success", state="complete")
                    else:
                        # Provide helpful context for "URL not found" errors
                        if 'not found' in result['message'].lower():
                            st.write(f"   ❌ {result['message']}")
                            st.write(f"   💡 Common reasons: link may be in a widget, shortcode, custom field, or theme template")
                        else:
                            st.write(f"   ❌ {result['message']}")
                        
                        results.append({
                            'source_url': fix['source_url'],
                            'broken_url': fix['broken_url'],
                            'action': fix['action'],
                            'status': 'failed',
                            'message': result['message']
                        })
                        status.update(label=f"❌ Failed", state="error")
                        
                except Exception as e:
                    st.write(f"   ❌ Error: {str(e)}")
                    results.append({
                        'source_url': fix['source_url'],
                        'broken_url': fix['broken_url'],
                        'action': fix['action'],
                        'status': 'failed',
                        'message': str(e)
                    })
                    status.update(label=f"❌ Error", state="error")
            
            # Small delay to be nice to the server
            time.sleep(0.3)
    
    # Store results
    st.session_state.wp_execute_results = results
    st.session_state.wp_was_test_run = is_test_run
    
    # Track execution
    success = sum(1 for r in results if r['status'] == 'success')
    skipped = sum(1 for r in results if r['status'] == 'skipped')
    failed = sum(1 for r in results if r['status'] == 'failed')
    
    track_event("wordpress_apply", {
        "mode": "agent_test_run" if is_test_run else "agent",
        "total_fixes": len(results),
        "success": success,
        "skipped": skipped,
        "failed": failed
    })
    
    # Summary
    st.markdown("---")
    if is_test_run:
        st.markdown("### 🧪 Test Run Complete!")
    else:
        st.markdown("### 📊 Execution Complete")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Success", success)
    with col2:
        st.metric("⏭️ Skipped", skipped)
    with col3:
        st.metric("❌ Failed", failed)
    
    # Test run follow-up
    if is_test_run and success > 0:
        total_pages = st.session_state.source_pages_count
        remaining_pages = total_pages - AGENT_MODE_LIMIT
        
        st.markdown("---")
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); padding: 1.25rem; border-radius: 10px; border: 1px solid #6ee7b7;">
            <div style="font-weight: 600; color: #065f46; font-size: 1.1rem; margin-bottom: 0.5rem;">✅ Test Run Successful!</div>
            <div style="color: #047857; margin-bottom: 1rem;">
                You've verified that Screaming Fixes works on your site. 
                <strong>{remaining_pages} more pages</strong> are waiting to be fixed.
            </div>
            <div style="font-weight: 600; color: #065f46; margin-bottom: 0.5rem;">Next Steps:</div>
            <div style="color: #047857;">
                1. Set up <strong>Fast Mode</strong> in Screaming Frog (2 min setup)<br>
                2. Re-crawl your site to capture Post IDs<br>
                3. Re-upload your CSV — all {total_pages} pages will be ready to fix
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("📋 Set up Fast Mode now", expanded=True):
            render_post_id_extraction_guide()
    
    # Handle skipped pages
    if skipped_for_retry:
        st.markdown("---")
        st.warning(f"**{len(skipped_for_retry)} pages** were skipped because Post ID could not be found.")
        
        with st.expander("Enter Post IDs manually for skipped pages"):
            for fix in skipped_for_retry:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(fix['source_url'][:60] + "..." if len(fix['source_url']) > 60 else fix['source_url'])
                with col2:
                    post_id_input = st.text_input(
                        "Post ID",
                        key=f"manual_postid_{fix['source_url']}",
                        label_visibility='collapsed',
                        placeholder="Post ID"
                    )
                    if post_id_input and post_id_input.isdigit():
                        st.session_state.post_id_cache[fix['source_url']] = int(post_id_input)
            
            if st.button("🔄 Retry Skipped Pages"):
                st.rerun()


def apply_fixes_to_wordpress(dry_run: bool = True):
    """Apply approved fixes to WordPress"""
    if not st.session_state.wp_client:
        st.error("WordPress not connected")
        return
    
    client = st.session_state.wp_client
    export_data = create_export_data()
    
    if not export_data:
        st.warning("No fixes to apply")
        return
    
    mode = "Preview" if dry_run else "Execution"
    
    with st.status(f"Running {mode}...", expanded=True) as status:
        results = []
        
        for i, fix in enumerate(export_data):
            st.write(f"Processing {i+1}/{len(export_data)}: `{fix['source_url'][:50]}...`")
            
            try:
                # Find post ID from source URL
                post_id = client.find_post_id_by_url(fix['source_url'])
                if not post_id:
                    results.append({
                        'source_url': fix['source_url'],
                        'broken_url': fix['broken_url'],
                        'action': fix['action'],
                        'status': 'skipped',
                        'message': 'Post ID not found'
                    })
                    continue
                
                # Apply fix (or preview)
                if fix['action'] == 'remove':
                    result = client.remove_link(post_id, fix['broken_url'], dry_run=dry_run)
                else:
                    result = client.replace_link(post_id, fix['broken_url'], fix['replacement_url'], dry_run=dry_run)
                
                results.append({
                    'source_url': fix['source_url'],
                    'broken_url': fix['broken_url'],
                    'action': fix['action'],
                    'status': 'success' if result['success'] else 'failed',
                    'message': result['message']
                })
            except Exception as e:
                results.append({
                    'source_url': fix['source_url'],
                    'broken_url': fix['broken_url'],
                    'action': fix['action'],
                    'status': 'failed',
                    'message': str(e)
                })
        
        # Store results
        if dry_run:
            st.session_state.wp_preview_results = results
            st.session_state.wp_preview_done = True
        else:
            st.session_state.wp_execute_results = results
            st.session_state.wp_preview_done = False  # Reset for next batch
        
        # Summary
        success = sum(1 for r in results if r['status'] == 'success')
        skipped = sum(1 for r in results if r['status'] == 'skipped')
        failed = sum(1 for r in results if r['status'] == 'failed')
        
        # Track WordPress apply (counts only, no URLs)
        track_event("wordpress_apply", {
            "mode": "preview" if dry_run else "execute",
            "total_fixes": len(results),
            "success": success,
            "skipped": skipped,
            "failed": failed
        })
        
        status.update(
            label=f"✅ {mode} complete: {success} successful, {skipped} skipped, {failed} failed",
            state="complete"
        )


def render_wp_results(is_test_run: bool = False):
    """Render WordPress results table"""
    # Show execute results if available, else preview results
    results = st.session_state.get('wp_execute_results') or st.session_state.get('wp_preview_results')
    
    if not results:
        return
    
    is_preview = st.session_state.get('wp_execute_results') is None
    was_test_run = st.session_state.get('wp_was_test_run', False)
    
    if was_test_run:
        st.markdown("### 🧪 Test Run Results")
    elif is_preview:
        st.markdown("### Preview Results")
    else:
        st.markdown("### Execution Results")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total", len(results))
    with col2:
        st.metric("✅ Success", sum(1 for r in results if r['status'] == 'success'))
    with col3:
        st.metric("⏭️ Skipped", sum(1 for r in results if r['status'] == 'skipped'))
    with col4:
        st.metric("❌ Failed", sum(1 for r in results if r['status'] == 'failed'))
    
    # Results table (shortened for readability)
    df = pd.DataFrame([
        {
            'Source URL': r['source_url'][:50] + '...' if len(r['source_url']) > 50 else r['source_url'],
            'Broken URL': r['broken_url'][:40] + '...' if len(r['broken_url']) > 40 else r['broken_url'],
            'Action': r['action'].upper(),
            'Status': r['status'].upper(),
            'Message': r['message']
        }
        for r in results
    ])
    
    st.dataframe(df, use_container_width=True)
    
    # Full URLs expander for copy/paste
    with st.expander("📋 View Full URLs (for copy/paste)"):
        for i, r in enumerate(results):
            status_icon = "✅" if r['status'] == 'success' else ("⏭️" if r['status'] == 'skipped' else "❌")
            st.markdown(f"**{status_icon} Result {i+1}**")
            st.code(f"Source URL: {r['source_url']}\nBroken URL: {r['broken_url']}", language=None)
            st.markdown(f"Action: `{r['action'].upper()}` | Status: `{r['status'].upper()}` | {r['message']}")
            if i < len(results) - 1:
                st.markdown("---")
    
    # Download results
    csv_output = pd.DataFrame(results).to_csv(index=False)
    mode = "preview" if is_preview else "executed"
    
    st.download_button(
        label="📥 Download Results CSV",
        data=csv_output,
        file_name=f"screaming_fixes_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )


def create_export_data() -> List[Dict]:
    """Create export data from approved decisions"""
    decisions = st.session_state.decisions
    broken_urls = st.session_state.broken_urls
    
    export = []
    
    for url, decision in decisions.items():
        if not decision['approved_action'] or decision['approved_action'] == 'ignore':
            continue
        
        info = broken_urls[url]
        
        for source in info['sources']:
            export.append({
                'source_url': source,
                'broken_url': url,
                'status_code': info['status_code'],
                'is_internal': info['is_internal'],
                'action': decision['approved_action'],
                'replacement_url': decision['approved_fix'] if decision['approved_action'] == 'replace' else '',
            })
    
    return export


def create_rc_export_data() -> List[Dict]:
    """Create export data from approved redirect chain decisions"""
    decisions = st.session_state.rc_decisions
    redirects = st.session_state.rc_redirects
    
    export = []
    
    for key, decision in decisions.items():
        if not decision['approved_action']:
            continue
        
        info = redirects[key]
        
        for source in info['sources']:
            export.append({
                'source_url': source,
                'old_url': info['address'],
                'new_url': info['final_address'],
                'redirect_type': '302 (Temporary)' if info['is_temp_redirect'] else '301 (Permanent)',
                'hops': info['num_hops'],
                'action': 'replace',
            })
    
    return export


def render_task_switcher():
    """Render task type switcher dropdown"""
    # Count items in each task type
    broken_count = len(st.session_state.broken_urls) if st.session_state.broken_urls else 0
    broken_pending = sum(1 for d in st.session_state.decisions.values() if not d.get('approved_action')) if st.session_state.decisions else 0
    
    rc_count = len(st.session_state.rc_redirects) if st.session_state.rc_redirects else 0
    rc_pending = sum(1 for d in st.session_state.rc_decisions.values() if not d.get('approved_action')) if st.session_state.rc_decisions else 0
    
    # Build options list
    options = []
    option_labels = []
    
    if broken_count > 0:
        options.append('broken_links')
        option_labels.append(f"🔗 Broken Links ({broken_pending} pending)" if broken_pending > 0 else f"🔗 Broken Links (✓ {broken_count} done)")
    
    if rc_count > 0:
        options.append('redirect_chains')
        option_labels.append(f"🔄 Redirect Chains ({rc_pending} pending)" if rc_pending > 0 else f"🔄 Redirect Chains (✓ {rc_count} done)")
    
    # Only show switcher if we have multiple task types
    if len(options) <= 1:
        return
    
    current_idx = options.index(st.session_state.current_task) if st.session_state.current_task in options else 0
    
    selected = st.selectbox(
        "Current Task:",
        options,
        index=current_idx,
        format_func=lambda x: option_labels[options.index(x)],
        key="task_switcher"
    )
    
    if selected != st.session_state.current_task:
        st.session_state.current_task = selected
        st.rerun()


def render_rc_metrics():
    """Render summary metrics for redirect chains"""
    redirects = st.session_state.rc_redirects
    decisions = st.session_state.rc_decisions
    sitewide = st.session_state.rc_sitewide
    loops = st.session_state.rc_loops
    
    total = len(redirects)
    permanent = sum(1 for r in redirects.values() if not r['is_temp_redirect'])
    temporary = total - permanent
    approved = sum(1 for d in decisions.values() if d['approved_action'])
    pending = total - approved
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Redirects", total)
    with col2:
        st.metric("301 Permanent", permanent)
    with col3:
        st.metric("302 Temporary ⚠️", temporary)
    with col4:
        st.metric("✅ Approved", approved)


def render_rc_warnings():
    """Render sitewide links and loops warnings"""
    sitewide = st.session_state.rc_sitewide
    loops = st.session_state.rc_loops
    
    if sitewide:
        with st.expander(f"⚠️ Sitewide Links Detected ({len(sitewide)}) — Manual Fix Required", expanded=False):
            st.markdown("""
            These redirect chains appear in your **header, footer, or sidebar** across your entire site.
            They should be updated manually in your theme or widget settings — fixing them in one place fixes them everywhere.
            """)
            
            for item in sitewide[:10]:  # Show first 10
                st.markdown(f"""
                <div style="background: #fef3c7; padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem; border-left: 3px solid #f59e0b;">
                    <div style="font-family: monospace; font-size: 0.85rem; color: #92400e; word-break: break-all;">
                        {item['address'][:60]}{'...' if len(item['address']) > 60 else ''}<br>
                        → {item['final_address'][:60]}{'...' if len(item['final_address']) > 60 else ''}
                    </div>
                    <div style="font-size: 0.8rem; color: #a16207; margin-top: 0.25rem;">
                        Position: {item['position']} • Affects {item['count']} pages
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            if len(sitewide) > 10:
                st.info(f"...and {len(sitewide) - 10} more sitewide links")
    
    if loops:
        with st.expander(f"🔄 Redirect Loops Detected ({len(loops)}) — Cannot Auto-Fix", expanded=False):
            st.markdown("""
            These URLs create **infinite redirect loops**. This is typically a server configuration issue, not a content issue.
            
            💡 **Tip:** Check your `.htaccess` file or redirect plugin for conflicting rules. Contact your hosting provider if unsure.
            """)
            
            for item in loops[:10]:  # Show first 10
                st.markdown(f"""
                <div style="background: #fee2e2; padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem; border-left: 3px solid #ef4444;">
                    <div style="font-family: monospace; font-size: 0.85rem; color: #991b1b; word-break: break-all;">
                        {item['address'][:60]}{'...' if len(item['address']) > 60 else ''}<br>
                        → {item['final_address'][:60]}{'...' if len(item['final_address']) > 60 else ''} (LOOP)
                    </div>
                    <div style="font-size: 0.8rem; color: #b91c1c; margin-top: 0.25rem;">
                        Affects {item['count']} pages
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            if len(loops) > 10:
                st.info(f"...and {len(loops) - 10} more loops")


def render_rc_spreadsheet():
    """Render the redirect chains spreadsheet view"""
    redirects = st.session_state.rc_redirects
    decisions = st.session_state.rc_decisions
    domain = st.session_state.rc_domain
    
    # User guidance
    with st.expander("📖 How to use this tool", expanded=False):
        st.markdown("""
        **Review each redirect and approve the fix:**
        
        1. **Click on a redirect row** to expand it and see your options
        2. **Review the redirect** — old URL → new URL
        3. **Approve the fix** — Screaming Frog already knows the final destination, so just approve to update your links
        4. **Export or Apply** — Once approved, export as CSV or apply directly to WordPress
        
        💡 **Tip:** Not all redirects need fixing — use your judgment. Some redirects are intentional, like affiliate links or tracking URLs that redirect to a final destination. Review before approving.
        """)
    
    # Filters
    st.markdown("**Filters:**")
    filter_cols = st.columns(4)
    with filter_cols[0]:
        st.session_state.rc_filter_301 = st.checkbox("301 Permanent", value=True, key="rc_301")
    with filter_cols[1]:
        st.session_state.rc_filter_302 = st.checkbox("302 Temporary ⚠️", value=True, key="rc_302")
    with filter_cols[2]:
        st.session_state.rc_show_pending = st.checkbox("Pending", value=True, key="rc_pending")
    with filter_cols[3]:
        st.session_state.rc_show_approved = st.checkbox("Approved", value=True, key="rc_approved")
    
    # Count pending URLs for bulk actions
    pending_keys = [k for k, d in decisions.items() if not d['approved_action']]
    
    # Bulk actions
    if pending_keys:
        with st.expander(f"⚡ Bulk Actions ({len(pending_keys)} pending)", expanded=False):
            st.markdown("Redirect chains are safe to bulk approve since the replacement URLs are already verified by Screaming Frog:")
            
            if st.button(f"✅ Approve All Pending ({len(pending_keys)})", use_container_width=True, type="primary"):
                for key in pending_keys:
                    st.session_state.rc_decisions[key]['approved_action'] = 'replace'
                    st.session_state.rc_decisions[key]['approved_fix'] = redirects[key]['final_address']
                st.toast(f"✅ Approved {len(pending_keys)} redirects", icon="✅")
                time.sleep(0.5)
                st.rerun()
    
    # Apply filters
    filtered_keys = []
    for key, info in redirects.items():
        # Filter by redirect type
        if info['is_temp_redirect'] and not st.session_state.rc_filter_302:
            continue
        if not info['is_temp_redirect'] and not st.session_state.rc_filter_301:
            continue
        
        # Filter by approval status
        has_approval = bool(decisions[key]['approved_action'])
        if has_approval and not st.session_state.rc_show_approved:
            continue
        if not has_approval and not st.session_state.rc_show_pending:
            continue
        
        filtered_keys.append(key)
    
    if not filtered_keys:
        st.info("No redirects match your filters")
        return
    
    # Sort by impact (most pages affected first)
    filtered_keys.sort(key=lambda k: redirects[k]['count'], reverse=True)
    
    # Pagination
    total = len(filtered_keys)
    per_page = 10
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(st.session_state.rc_page, total_pages - 1)
    
    start = page * per_page
    end = min(start + per_page, total)
    page_keys = filtered_keys[start:end]
    
    st.markdown(f"**Showing {start+1}-{end} of {total} redirect chains**")
    
    # Render each redirect
    for key in page_keys:
        render_rc_row(key, redirects[key], decisions[key])
    
    # Pagination
    if total_pages > 1:
        pcol1, pcol2, pcol3 = st.columns([1, 2, 1])
        with pcol1:
            if st.button("← Previous", disabled=page == 0, key="rc_prev"):
                st.session_state.rc_page = page - 1
                st.rerun()
        with pcol2:
            st.markdown(f"<div style='text-align:center; padding-top: 0.5rem;'>Page {page+1} of {total_pages}</div>", unsafe_allow_html=True)
        with pcol3:
            if st.button("Next →", disabled=page >= total_pages - 1, key="rc_next"):
                st.session_state.rc_page = page + 1
                st.rerun()


def render_rc_row(key: str, info: Dict, decision: Dict):
    """Render a single redirect chain row"""
    
    # Type badge
    if info['is_temp_redirect']:
        type_badge = '<span class="status-badge" style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); color: #b45309;">302 Temp ⚠️</span>'
    else:
        type_badge = '<span class="status-badge" style="background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); color: #059669;">301 Perm</span>'
    
    # Internal/External badge
    int_ext_badge = '<span class="status-badge status-internal">Internal</span>' if info['is_internal'] else '<span class="status-badge status-external">External</span>'
    
    # Approval status badge
    if decision['approved_action']:
        status_badge = '<span class="approved-badge">✓ Approved</span>'
    else:
        status_badge = '<span class="pending-badge">⏳ Pending</span>'
    
    # Shorten URLs for display
    old_url_short = info['address'][:50] + '...' if len(info['address']) > 50 else info['address']
    new_url_short = info['final_address'][:50] + '...' if len(info['final_address']) > 50 else info['final_address']
    
    st.markdown(f"""
    <div class="url-row">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
            <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
                {type_badge}
                {int_ext_badge}
                {status_badge}
            </div>
            <div style="color: #64748b; font-size: 0.8rem;">Affects {info['count']} page(s)</div>
        </div>
        <div style="font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.8rem; color: #dc2626; word-break: break-all;">
            ✗ {old_url_short}
        </div>
        <div style="font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.8rem; color: #059669; word-break: break-all; margin-top: 0.25rem;">
            → {new_url_short}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Action area
    is_editing = st.session_state.rc_editing_url == key
    
    col1, col2 = st.columns([1, 5])
    with col1:
        if is_editing:
            if st.button("❌ Close", key=f"rc_close_{key}", use_container_width=True):
                st.session_state.rc_editing_url = None
                st.rerun()
        else:
            if st.button("📝 Review", key=f"rc_edit_{key}", use_container_width=True):
                st.session_state.rc_editing_url = key
                st.rerun()
    
    # Show inline edit form if this redirect is being edited
    if is_editing:
        st.markdown("""
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem; margin-top: 0.5rem;">
        """, unsafe_allow_html=True)
        
        st.markdown("**Redirect Details:**")
        
        # Show full URLs
        st.markdown(f"**Current URL (will be replaced):**")
        st.code(info['address'], language=None)
        
        st.markdown(f"**Final URL (replacement):**")
        st.code(info['final_address'], language=None)
        
        if info['is_temp_redirect']:
            st.warning("⚠️ This is a **302 Temporary** redirect. The destination may revert. Update if you're confident it's stable.")
        
        # Show affected pages
        with st.expander(f"📄 Affected pages ({len(info['sources'])})", expanded=False):
            for source in info['sources'][:10]:
                st.markdown(f"- `{source[:60]}{'...' if len(source) > 60 else ''}`")
            if len(info['sources']) > 10:
                st.info(f"...and {len(info['sources']) - 10} more pages")
        
        st.markdown("---")
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Approve Fix", key=f"rc_approve_{key}", type="primary", use_container_width=True):
                st.session_state.rc_decisions[key]['approved_action'] = 'replace'
                st.session_state.rc_decisions[key]['approved_fix'] = info['final_address']
                st.session_state.rc_editing_url = None
                st.toast("✅ Redirect approved!", icon="✅")
                time.sleep(0.3)
                st.rerun()
        
        with col2:
            if decision['approved_action']:
                if st.button("↩️ Reset", key=f"rc_reset_{key}", use_container_width=True):
                    st.session_state.rc_decisions[key]['approved_action'] = ''
                    st.session_state.rc_decisions[key]['approved_fix'] = ''
                    st.session_state.rc_editing_url = None
                    st.toast("↩️ Reset to pending", icon="↩️")
                    time.sleep(0.3)
                    st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)


def render_rc_export_section():
    """Render export section for redirect chains"""
    decisions = st.session_state.rc_decisions
    redirects = st.session_state.rc_redirects
    
    approved = [(k, d) for k, d in decisions.items() if d['approved_action']]
    has_approved = len(approved) > 0
    
    st.markdown('<p class="section-header">Export & Apply</p>', unsafe_allow_html=True)
    
    # Status message based on approved count
    if has_approved:
        # Count total pages affected
        total_pages = sum(len(redirects[k]['sources']) for k, d in approved)
        st.markdown(f"✅ **{len(approved)} redirects approved** affecting {total_pages} pages")
    else:
        st.markdown("No redirects approved yet. Approve fixes above to enable export.")
    
    # Export buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export CSV", use_container_width=True, disabled=not has_approved, key="rc_export_csv"):
            export_data = create_rc_export_data()
            
            track_event("export", {
                "format": "csv",
                "type": "redirect_chains",
                "total_fixes": len(export_data),
            })
            
            csv_data = pd.DataFrame(export_data).to_csv(index=False)
            st.download_button(
                "Download CSV",
                data=csv_data,
                file_name=f"redirect_chain_fixes_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="rc_download_csv"
            )
    
    with col2:
        if st.button("📥 Export JSON", use_container_width=True, disabled=not has_approved, key="rc_export_json"):
            export_data = create_rc_export_data()
            
            track_event("export", {
                "format": "json",
                "type": "redirect_chains",
                "total_fixes": len(export_data),
            })
            
            json_data = json.dumps(export_data, indent=2)
            st.download_button(
                "Download JSON",
                data=json_data,
                file_name=f"redirect_chain_fixes_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True,
                key="rc_download_json"
            )
    
    # WordPress apply section
    if not st.session_state.wp_connected:
        return
    
    st.markdown("---")
    st.markdown("**Apply directly to WordPress:**")
    
    if not has_approved:
        st.info("Approve some redirects above first")
        return
    
    # Count how many source pages need fixes
    source_pages_to_fix = set()
    for key, decision in approved:
        for source in redirects[key]['sources']:
            source_pages_to_fix.add(source)
    
    pages_to_fix = len(source_pages_to_fix)
    selected_mode = st.session_state.get('selected_mode', 'agent')
    
    if selected_mode == 'agent' and pages_to_fix <= AGENT_MODE_LIMIT:
        st.info(f"🤖 **Agent Mode:** {pages_to_fix} pages to update")
        
        if not st.session_state.post_id_check_done:
            st.markdown("Before applying, let's verify your site supports automatic Post ID discovery.")
            if st.button("🔍 Run Compatibility Check", use_container_width=True, key="rc_check"):
                run_post_id_sample_check(list(source_pages_to_fix)[:3])
        else:
            if st.session_state.post_id_check_passed:
                st.success("✅ Compatibility check passed!")
                if st.button("🚀 Apply Redirect Fixes to WordPress", type="primary", use_container_width=True, key="rc_apply"):
                    run_rc_agent_fixes(approved, source_pages_to_fix)
            else:
                st.error("❌ Automatic Post ID lookup failed.")
                st.info("💡 Try setting up Enterprise Mode for more reliable Post ID handling.")
    else:
        st.warning(f"⚠️ {pages_to_fix} pages exceeds Agent Mode limit ({AGENT_MODE_LIMIT}). Use Enterprise Mode or export CSV for manual updates.")


def run_rc_agent_fixes(approved: List, source_pages_to_fix: set):
    """Run the agent to apply redirect chain fixes"""
    client = st.session_state.wp_client
    redirects = st.session_state.rc_redirects
    
    # Build list of all fixes to apply
    fixes_to_apply = []
    for key, decision in approved:
        info = redirects[key]
        for source in info['sources']:
            if source in source_pages_to_fix:
                fixes_to_apply.append({
                    'source_url': source,
                    'old_url': info['address'],
                    'new_url': info['final_address'],
                    'post_id': st.session_state.post_id_cache.get(source)
                })
    
    total_fixes = len(fixes_to_apply)
    results = []
    
    st.markdown("### 🔄 Applying Redirect Fixes")
    
    progress_bar = st.progress(0)
    status_container = st.container()
    
    with status_container:
        for i, fix in enumerate(fixes_to_apply):
            progress_bar.progress((i + 1) / total_fixes)
            
            with st.status(f"Fix {i+1} of {total_fixes}", expanded=True) as status:
                # Step 1: Get Post ID
                post_id = fix['post_id']
                
                if not post_id:
                    st.write(f"🔍 Finding Post ID for: `{fix['source_url'][:50]}...`")
                    post_id = client.find_post_id_by_url(fix['source_url'])
                    
                    if post_id:
                        st.write(f"   ✅ Found Post ID: {post_id}")
                        st.session_state.post_id_cache[fix['source_url']] = post_id
                    else:
                        # Check if it's a category/archive/tag page
                        source_lower = fix['source_url'].lower()
                        is_archive = any(x in source_lower for x in ['/category/', '/tag/', '/author/', '/page/', '/archive/'])
                        
                        if is_archive:
                            st.write(f"   ℹ️ This is an archive/category page (dynamically generated)")
                            st.write(f"   💡 Fix the links on individual posts — archive pages will update automatically")
                            msg = 'Archive/category page - fix individual posts instead'
                        else:
                            st.write(f"   ❌ Post ID not found — skipping")
                            msg = 'Post ID not found'
                        
                        results.append({
                            'source_url': fix['source_url'],
                            'old_url': fix['old_url'],
                            'new_url': fix['new_url'],
                            'status': 'skipped',
                            'message': msg
                        })
                        status.update(label=f"⏭️ Skipped", state="error")
                        continue
                else:
                    st.write(f"📄 Post ID: {post_id}")
                
                # Step 2: Apply fix (replace old URL with new URL)
                st.write(f"🔧 Replacing URL...")
                st.write(f"   Old: `{fix['old_url'][:40]}...`")
                st.write(f"   New: `{fix['new_url'][:40]}...`")
                
                try:
                    result = client.replace_link(post_id, fix['old_url'], fix['new_url'], dry_run=False)
                    
                    if result['success']:
                        st.write(f"   ✅ {result['message']}")
                        results.append({
                            'source_url': fix['source_url'],
                            'old_url': fix['old_url'],
                            'new_url': fix['new_url'],
                            'status': 'success',
                            'message': result['message']
                        })
                        status.update(label=f"✅ Success", state="complete")
                    else:
                        # Provide helpful context for "URL not found" errors
                        if 'not found' in result['message'].lower():
                            st.write(f"   ❌ {result['message']}")
                            st.write(f"   💡 Common reasons: link may be in a widget, shortcode, custom field, or theme template")
                        else:
                            st.write(f"   ❌ {result['message']}")
                        
                        results.append({
                            'source_url': fix['source_url'],
                            'old_url': fix['old_url'],
                            'new_url': fix['new_url'],
                            'status': 'failed',
                            'message': result['message']
                        })
                        status.update(label=f"❌ Failed", state="error")
                        
                except Exception as e:
                    st.write(f"   ❌ Error: {str(e)}")
                    results.append({
                        'source_url': fix['source_url'],
                        'old_url': fix['old_url'],
                        'new_url': fix['new_url'],
                        'status': 'failed',
                        'message': str(e)
                    })
                    status.update(label=f"❌ Error", state="error")
            
            time.sleep(0.3)
    
    # Store results
    st.session_state.wp_execute_results = results
    
    # Summary
    success = sum(1 for r in results if r['status'] == 'success')
    skipped = sum(1 for r in results if r['status'] == 'skipped')
    failed = sum(1 for r in results if r['status'] == 'failed')
    
    track_event("wordpress_apply", {
        "type": "redirect_chains",
        "total_fixes": len(results),
        "success": success,
        "skipped": skipped,
        "failed": failed
    })
    
    st.markdown("---")
    st.markdown("### 📊 Execution Complete")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Success", success)
    with col2:
        st.metric("⏭️ Skipped", skipped)
    with col3:
        st.metric("❌ Failed", failed)


def render_about():
    """Render the About section"""
    st.markdown('<p class="section-header" id="about">About</p>', unsafe_allow_html=True)
    
    st.markdown("""
    **Screaming Fixes** is a free, open-source tool built for SEO professionals who are tired of manually 
    updating broken links and redirect chains one by one.
    
    *We are not affiliated with, sponsored by, or endorsed by [Screaming Frog SEO Spider](https://www.screamingfrog.co.uk/seo-spider/). 
    We just love using their tool and wanted to help SEOs get even more value from it.*
    
    **What this tool does:**
    - **Broken Links:** Groups thousands of link references by unique broken URL, with optional AI suggestions
    - **Redirect Chains:** Bulk updates outdated URLs to their final destinations (no AI needed!)
    - Requires **human approval** for all fixes before they're applied
    - **Fixes and publishes updates** directly to your live WordPress website
    - Exports to CSV/JSON for use with WordPress or any CMS
    
    **Key insight:** Your Screaming Frog export might have 7,000+ link references, but only 60-100 unique URLs to fix. 
    Fix each unique URL once, and you've fixed them all.
    
    Your data never leaves your browser session. [View the source code](https://github.com/backofnapkin/screaming-fixes) to verify.
    """)
    
    st.markdown("""
    ---
    **⚠️ Disclaimer:** This tool is provided "as-is" without warranty of any kind. You are solely responsible for 
    reviewing, approving, and applying any changes to your website. Screaming Frog data may occasionally contain 
    errors or false positives. Always back up your site before making bulk changes. The creators of this tool 
    are not liable for any damages or issues resulting from its use.
    """)


def render_instructions():
    """Render the Instructions section"""
    st.markdown('<p class="section-header" id="instructions">Instructions</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("📋 How to Export Broken Links", expanded=True):
            st.markdown("""
            1. Run your crawl in Screaming Frog
            2. Go to **Bulk Export** menu
            3. Select **Response Codes → Client Error (4xx) → Inlinks**
            4. Save the CSV file
            5. Upload it here
            
            This exports all internal pages that link to broken URLs, 
            including the anchor text used.
            """)
        
        with st.expander("🔄 How to Export Redirect Chains"):
            st.markdown("""
            1. Run your crawl in Screaming Frog
            2. Go to **Reports** menu
            3. Select **Redirects → All Redirects**
            4. Save the CSV file
            5. Upload it here
            
            This exports all redirect chains found during the crawl,
            along with the final destination URLs.
            """)
        
        with st.expander("🤖 Getting AI Suggestions (Broken Links only)"):
            st.markdown("""
            1. Get an API key from [console.anthropic.com](https://console.anthropic.com)
            2. Paste it in the "AI Suggestions" section
            3. Click "Get AI Suggestion" on any broken URL
            4. Claude will search the web for replacements
            5. **Review and approve** before applying
            
            *Cost: ~$0.01-0.05 per suggestion with web search*
            
            **Note:** Redirect chains don't need AI — the replacement URL is already known!
            """)
    
    with col2:
        with st.expander("🔐 WordPress Application Passwords"):
            st.markdown("""
            Application Passwords let external apps access your site securely:
            
            1. Go to **WordPress Admin → Users → Profile**
            2. Scroll to **Application Passwords**
            3. Enter name: `Screaming Fixes`
            4. Click **Add New Application Password**
            5. Copy the password (spaces are OK)
            
            *Requires WordPress 5.6+ or the Application Passwords plugin*
            """)
        
        with st.expander("✅ Approving & Applying Fixes"):
            st.markdown("""
            For each broken URL, you can:
            
            - **🗑️ Remove** — Delete the link, keep the anchor text
            - **✓ Use Manual** — Use the URL you typed
            - **✓ Use AI** — Accept Claude's suggestion
            
            Then either:
            - **Export CSV/JSON** for manual updates
            - **Apply to WordPress** directly via REST API
            
            Nothing is applied until you approve it.
            """)


def render_footer():
    """Render footer"""
    st.markdown("---")
    st.markdown("""
    <div class="footer">
        <div style="display: flex; justify-content: center; gap: 8px; margin-bottom: 1rem;">
            <a href="https://github.com/backofnapkin/screaming-fixes" target="_blank">
                <img src="https://img.shields.io/badge/GitHub-View_Source-134e4a?style=flat-square&logo=github" alt="GitHub">
            </a>
            <a href="https://streamlit.io" target="_blank">
                <img src="https://img.shields.io/badge/Powered_by-Streamlit-14b8a6?style=flat-square" alt="Streamlit">
            </a>
        </div>
        Built with ❤️ for the SEO community
        <div style="margin-top: 1rem; font-size: 0.75rem; color: #94a3b8;">
            <strong>Privacy:</strong> Your credentials and file contents are processed in your browser session only and are never stored. 
            We collect anonymous usage analytics (feature usage, error rates) to improve the tool. No personal data or URLs are tracked.
        </div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# MAIN
# =============================================================================

def render_progress_indicator():
    """Render workflow progress indicator"""
    decisions = st.session_state.decisions
    
    # Determine current state
    has_upload = st.session_state.df is not None
    has_reviewed = any(d['approved_action'] for d in decisions.values()) if decisions else False
    all_reviewed = all(d['approved_action'] for d in decisions.values()) if decisions else False
    approved_count = sum(1 for d in decisions.values() if d['approved_action'] and d['approved_action'] != 'ignore')
    has_exports = approved_count > 0
    
    # Step states: 'complete', 'active', 'pending'
    step1 = 'complete' if has_upload else 'active'
    step2 = 'complete' if all_reviewed else ('active' if has_upload else 'pending')
    step3 = 'complete' if has_exports else ('active' if has_reviewed else 'pending')
    step4 = 'active' if has_exports else 'pending'
    
    def get_circle_style(state):
        if state == 'complete':
            return 'background: linear-gradient(135deg, #0d9488, #0891b2); color: white;'
        elif state == 'active':
            return 'background: linear-gradient(135deg, #ccfbf1, #a5f3fc); color: #0d9488; border: 2px solid #0d9488;'
        else:
            return 'background: #e2e8f0; color: #94a3b8;'
    
    def get_icon(state, num):
        return '✓' if state == 'complete' else num
    
    def get_connector_style(prev_state):
        if prev_state == 'complete':
            return 'background: linear-gradient(90deg, #0d9488, #0891b2);'
        else:
            return 'background: #e2e8f0;'
    
    def get_label_style(state):
        if state == 'complete':
            return 'color: #0d9488; font-weight: 600;'
        elif state == 'active':
            return 'color: #0d9488; font-weight: 600;'
        else:
            return 'color: #94a3b8;'
    
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: center; margin: 0.5rem 0 1.5rem 0;">
        <!-- Step 1 -->
        <div style="display: flex; flex-direction: column; align-items: center; min-width: 70px;">
            <div style="width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; {get_circle_style(step1)}">{get_icon(step1, '1')}</div>
            <div style="font-size: 0.75rem; margin-top: 0.35rem; {get_label_style(step1)}">Upload</div>
        </div>
        <!-- Connector 1-2 -->
        <div style="width: 40px; height: 3px; {get_connector_style(step1)} margin: 0 -5px; margin-bottom: 1.2rem;"></div>
        <!-- Step 2 -->
        <div style="display: flex; flex-direction: column; align-items: center; min-width: 70px;">
            <div style="width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; {get_circle_style(step2)}">{get_icon(step2, '2')}</div>
            <div style="font-size: 0.75rem; margin-top: 0.35rem; {get_label_style(step2)}">Review</div>
        </div>
        <!-- Connector 2-3 -->
        <div style="width: 40px; height: 3px; {get_connector_style(step2)} margin: 0 -5px; margin-bottom: 1.2rem;"></div>
        <!-- Step 3 -->
        <div style="display: flex; flex-direction: column; align-items: center; min-width: 70px;">
            <div style="width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; {get_circle_style(step3)}">{get_icon(step3, '3')}</div>
            <div style="font-size: 0.75rem; margin-top: 0.35rem; {get_label_style(step3)}">Approve</div>
        </div>
        <!-- Connector 3-4 -->
        <div style="width: 40px; height: 3px; {get_connector_style(step3)} margin: 0 -5px; margin-bottom: 1.2rem;"></div>
        <!-- Step 4 -->
        <div style="display: flex; flex-direction: column; align-items: center; min-width: 70px;">
            <div style="width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; {get_circle_style(step4)}">{get_icon(step4, '4')}</div>
            <div style="font-size: 0.75rem; margin-top: 0.35rem; {get_label_style(step4)}">Apply</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def main():
    init_session_state()
    render_nav()
    render_header()
    render_progress_indicator()
    
    # Check if we have any data loaded
    has_broken_links = st.session_state.df is not None
    has_redirect_chains = st.session_state.rc_df is not None
    
    if not has_broken_links and not has_redirect_chains:
        # No data loaded yet - show upload section
        render_upload_section()
    else:
        # Data loaded - show task switcher if multiple tasks
        render_task_switcher()
        
        # Mode status banner - shows Agent Mode / Enterprise Mode status
        render_mode_selector()
        
        # Render based on current task type
        current_task = st.session_state.current_task
        
        if current_task == 'redirect_chains' and has_redirect_chains:
            # Redirect Chains workflow
            st.markdown('<p class="section-header">🔄 Redirect Chains</p>', unsafe_allow_html=True)
            render_rc_metrics()
            st.markdown("---")
            render_rc_warnings()
            render_rc_spreadsheet()
            st.markdown("---")
            render_wordpress_section()
            st.markdown("---")
            render_rc_export_section()
        
        elif current_task == 'broken_links' and has_broken_links:
            # Broken Links workflow (existing)
            st.markdown('<p class="section-header">🔗 Broken Links</p>', unsafe_allow_html=True)
            render_metrics()
            st.markdown("---")
            render_spreadsheet()
            st.markdown("---")
            render_wordpress_section()
            st.markdown("---")
            render_export_section()
        
        else:
            # Fallback - show whatever data we have
            if has_redirect_chains:
                st.session_state.current_task = 'redirect_chains'
                st.rerun()
            elif has_broken_links:
                st.session_state.current_task = 'broken_links'
                st.rerun()
    
    render_about()
    render_instructions()
    render_footer()


if __name__ == "__main__":
    main()
