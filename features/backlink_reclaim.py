"""
Backlink Reclaim Feature - Fix broken backlinks by creating redirects.

This is a reusable component that can be used by both the landing page
and the main tool. It takes scan results from DataForSEO and guides
users through fixing broken backlinks.
"""

import re
import json
import csv
import io
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

import streamlit as st

# Import config for API keys
from config import AGENT_MODE_API_KEY

# Optional imports
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from services.wordpress import SEOService, NoCapablePluginError
    SEO_SERVICE_AVAILABLE = True
except ImportError:
    SEO_SERVICE_AVAILABLE = False

try:
    from services.claude_api import track_event
except ImportError:
    def track_event(event_name: str, metadata: Dict = None):
        pass  # No-op if not available


# =============================================================================
# SESSION STATE MANAGEMENT
# =============================================================================

def init_backlink_reclaim_state():
    """Initialize session state variables for backlink reclaim feature"""
    defaults = {
        'br_scan_results': None,  # The scan results object
        'br_domain': None,  # The scanned domain
        'br_grouped_pages': {},  # {"/dead-path/": {"count": X, "referrers": [...], ...}}
        # Fix decisions per dead page - matches Broken Links pattern
        'br_decisions': {},  # {"/dead-path/": {"fix_type": null|"redirect"|"ignore"|"restore", "redirect_target": "", "ai_suggested": False, "ai_notes": ""}}
        'br_processing': False,  # Loading state
        'br_processing_item': None,  # Currently processing item
        'br_completed_redirects': [],  # List of successfully created redirects
        'br_failed_redirects': [],  # List of failed redirect attempts
        'br_workflow_complete': False,  # Whether redirects have been created
        # UI state
        'br_page': 0,  # Current page for pagination
        'br_per_page': 10,  # Items per page
        'br_editing_path': None,  # Currently editing path (for expanded row)
        'br_show_approved': True,  # Filter: show approved items
        'br_show_pending': True,  # Filter: show pending items
        # Navigation/scroll flags
        'br_scroll_to_section': False,  # Scroll to section when coming from landing page
        'br_scroll_to_export': False,  # Scroll to export section
        'br_from_landing': False,  # User came from landing page (hide upload section initially)
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def reset_backlink_reclaim_state():
    """Reset all backlink reclaim state variables"""
    keys_to_reset = [
        'br_scan_results', 'br_domain', 'br_grouped_pages', 'br_decisions',
        'br_processing', 'br_processing_item', 'br_completed_redirects',
        'br_failed_redirects', 'br_workflow_complete', 'br_page',
        'br_editing_path', 'br_show_approved', 'br_show_pending',
        'br_scroll_to_section', 'br_scroll_to_export', 'br_from_landing'
    ]
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    init_backlink_reclaim_state()


def load_scan_results(scan_results: Dict, domain: str):
    """
    Load scan results into session state.

    Args:
        scan_results: Dict with 'backlinks' list from DataForSEO
        domain: The scanned domain
    """
    init_backlink_reclaim_state()

    st.session_state.br_scan_results = scan_results
    st.session_state.br_domain = domain

    # Group backlinks by dead page (target_url path)
    grouped = {}
    # Support both 'backlinks' and 'broken_backlinks' keys for compatibility
    backlinks = scan_results.get('broken_backlinks') or scan_results.get('backlinks', [])

    for bl in backlinks:
        target_url = bl.get('target_url', '')
        # Extract path from URL
        if target_url:
            from urllib.parse import urlparse
            parsed = urlparse(target_url)
            path = parsed.path or '/'

            if path not in grouped:
                grouped[path] = {
                    'count': 0,
                    'referrers': [],
                    'anchor_texts': [],
                    'http_codes': [],
                    'full_url': target_url,
                }

            grouped[path]['count'] += 1
            grouped[path]['referrers'].append({
                'domain': bl.get('referring_domain', ''),
                'url': bl.get('referring_url', ''),
                'anchor': bl.get('anchor_text', ''),
                'rank': bl.get('domain_rank', 0),
            })
            if bl.get('anchor_text'):
                grouped[path]['anchor_texts'].append(bl.get('anchor_text'))
            grouped[path]['http_codes'].append(bl.get('http_code', 404))

    # Sort by count (most backlinks first)
    sorted_grouped = dict(sorted(grouped.items(), key=lambda x: x[1]['count'], reverse=True))
    st.session_state.br_grouped_pages = sorted_grouped

    # Initialize decisions for each path
    st.session_state.br_decisions = {
        path: {
            'fix_type': None,  # null | "redirect" | "ignore" | "restore"
            'redirect_target': '',
            'ai_suggested': False,
            'ai_notes': ''
        }
        for path in sorted_grouped.keys()
    }


# =============================================================================
# AI SUGGESTION LOGIC
# =============================================================================

def get_redirect_suggestion(
    dead_path: str,
    domain: str,
    anchor_texts: List[str],
    api_key: str
) -> Dict[str, str]:
    """
    Get AI suggestion for redirect target.

    Args:
        dead_path: The dead URL path (e.g., "/old-post/")
        domain: The domain name
        anchor_texts: List of anchor texts used by referrers
        api_key: Anthropic API key

    Returns:
        Dict with 'target' (suggested path) and 'notes'
    """
    if not ANTHROPIC_AVAILABLE:
        return {'target': '', 'notes': 'Anthropic library not installed.'}

    # Track the request
    track_event("backlink_redirect_suggestion", {
        "domain": domain,
        "anchor_count": len(anchor_texts),
    })

    try:
        client = Anthropic(api_key=api_key)

        # Build anchor text context
        unique_anchors = list(set(anchor_texts))[:5]
        anchors_text = ', '.join(f'"{a}"' for a in unique_anchors) if unique_anchors else "(no anchor text)"

        prompt = f"""You are helping fix broken backlinks on {domain}.

A page at this path is returning 404 and has valuable backlinks pointing to it:

DEAD PAGE PATH: {dead_path}
ANCHOR TEXTS USED BY LINKING SITES: {anchors_text}

Your task:
1. Search {domain} to find if similar content exists at a different URL
2. Look for content that would be relevant to what the anchor texts suggest
3. Suggest the best redirect target on the same domain

IMPORTANT:
- The target MUST be on {domain}
- Prefer specific relevant pages over generic category pages
- Only suggest homepage (/) as a last resort
- If no good match exists, suggest the most relevant category or parent page

Respond in JSON format:
{{"target": "/suggested-path/", "notes": "brief explanation of why this target makes sense"}}

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
                target = result.get('target', '')
                # Ensure target starts with /
                if target and not target.startswith('/'):
                    target = '/' + target
                return {
                    'target': target,
                    'notes': result.get('notes', 'No explanation provided.')
                }
        except json.JSONDecodeError:
            pass

        return {'target': '', 'notes': result_text[:150] if result_text else 'Could not parse response.'}

    except Exception as e:
        return {'target': '', 'notes': f'Error: {str(e)[:100]}'}


# =============================================================================
# EXPORT FUNCTIONS
# =============================================================================

def generate_csv_export(decisions: Dict, domain: str, grouped_pages: Dict) -> str:
    """Generate CSV export of redirect decisions"""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(['Source URL', 'Target URL', 'Redirect Type', 'Fix Type', 'Backlink Count', 'Top Referrer'])

    for source_path, decision in decisions.items():
        fix_type = decision.get('fix_type')
        if not fix_type:
            continue  # Skip items without a fix set

        source_url = f"https://{domain}{source_path}"

        # Build target URL for redirects
        if fix_type == 'redirect':
            target = decision.get('redirect_target', '')
            if target.startswith('http'):
                target_url = target
            elif target.startswith('/'):
                target_url = f"https://{domain}{target}"
            else:
                target_url = f"https://{domain}/{target}"
        else:
            target_url = ''  # No target for ignore/restore

        # Get referrer info
        page_info = grouped_pages.get(source_path, {})
        backlink_count = page_info.get('count', 0)
        referrers = page_info.get('referrers', [])
        top_referrer = referrers[0]['domain'] if referrers else ''

        writer.writerow([source_url, target_url, '301' if fix_type == 'redirect' else '', fix_type, backlink_count, top_referrer])

    return output.getvalue()


def generate_htaccess_export(decisions: Dict, domain: str) -> str:
    """Generate .htaccess redirect rules"""
    lines = [
        "# Redirects generated by Screaming Fixes",
        f"# Domain: {domain}",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "# 301 Redirects",
    ]

    for source_path, decision in decisions.items():
        # Only include redirect type fixes
        if decision.get('fix_type') != 'redirect':
            continue

        target = decision.get('redirect_target', '')
        if not target:
            continue

        # Build target - can be relative path or full URL
        if target.startswith('http'):
            target_url = target
        elif target.startswith('/'):
            target_url = target  # Keep as relative for .htaccess
        else:
            target_url = f"/{target}"

        lines.append(f"Redirect 301 {source_path} {target_url}")

    return "\n".join(lines)


# =============================================================================
# UI COMPONENTS
# =============================================================================

def get_fix_counts() -> Dict[str, int]:
    """Get counts of items by fix status"""
    decisions = st.session_state.br_decisions
    counts = {
        'redirect': 0,
        'ignore': 0,
        'restore': 0,
        'pending': 0,
        'total': len(decisions)
    }
    for decision in decisions.values():
        fix_type = decision.get('fix_type')
        if fix_type == 'redirect':
            counts['redirect'] += 1
        elif fix_type == 'ignore':
            counts['ignore'] += 1
        elif fix_type == 'restore':
            counts['restore'] += 1
        else:
            counts['pending'] += 1
    return counts


def render_metrics():
    """Render the metrics section with counts"""
    domain = st.session_state.br_domain
    grouped_pages = st.session_state.br_grouped_pages
    total_backlinks = sum(p['count'] for p in grouped_pages.values())
    counts = get_fix_counts()

    # Main metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); border: 1px solid #fca5a5; border-radius: 8px; padding: 1rem; text-align: center;">
            <div style="font-size: 1.75rem; font-weight: 700; color: #dc2626;">{len(grouped_pages)}</div>
            <div style="font-size: 0.8rem; color: #991b1b;">Dead Pages</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); border: 1px solid #fcd34d; border-radius: 8px; padding: 1rem; text-align: center;">
            <div style="font-size: 1.75rem; font-weight: 700; color: #d97706;">{total_backlinks}</div>
            <div style="font-size: 0.8rem; color: #92400e;">Backlinks at Risk</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 100%); border: 1px solid #99f6e4; border-radius: 8px; padding: 1rem; text-align: center;">
            <div style="font-size: 1.75rem; font-weight: 700; color: #0d9488;">{counts['redirect']}</div>
            <div style="font-size: 0.8rem; color: #0f766e;">Redirects Set</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem; text-align: center;">
            <div style="font-size: 1.75rem; font-weight: 700; color: #64748b;">{counts['pending']}</div>
            <div style="font-size: 0.8rem; color: #475569;">Pending</div>
        </div>
        """, unsafe_allow_html=True)

    # Domain info
    st.markdown(f"""
    <div style="margin-top: 0.75rem; color: #64748b; font-size: 0.85rem;">
        Domain: <strong style="color: #0f172a;">{domain}</strong>
    </div>
    """, unsafe_allow_html=True)


def render_spreadsheet(api_key: str):
    """Render the main spreadsheet view with pagination - matches Broken Links style"""
    import html

    grouped_pages = st.session_state.br_grouped_pages
    decisions = st.session_state.br_decisions
    domain = st.session_state.br_domain

    # Custom CSS for teal checkboxes (override default blue)
    st.markdown("""
    <style>
        /* Teal checkbox styling */
        [data-testid="stCheckbox"] [data-baseweb="checkbox"][aria-checked="true"],
        [data-testid="stCheckbox"] div[role="checkbox"][aria-checked="true"],
        [data-baseweb="checkbox"][aria-checked="true"] > div:first-child,
        [aria-checked="true"][data-baseweb="checkbox"] > div:first-child {
            background-color: #0d9488 !important;
            border-color: #0d9488 !important;
        }
        [data-testid="stCheckbox"] svg, [data-baseweb="checkbox"] svg { fill: white !important; }
    </style>
    """, unsafe_allow_html=True)

    # Compact filters row - checkboxes and sort on one line
    filter_cols = st.columns([1, 1, 1.5, 2.5])

    with filter_cols[0]:
        st.session_state.br_show_pending = st.checkbox(
            "Pending", value=st.session_state.get('br_show_pending', True), key="br_f_pend"
        )

    with filter_cols[1]:
        st.session_state.br_show_approved = st.checkbox(
            "Fixed", value=st.session_state.get('br_show_approved', True), key="br_f_appr"
        )

    with filter_cols[2]:
        sort_option = st.selectbox(
            "Sort",
            ["Backlinks ↓", "Path A-Z"],
            index=0,
            key="br_sort_select",
            label_visibility="collapsed"
        )

    # Apply filters
    filtered_paths = []
    for path in grouped_pages.keys():
        decision = decisions.get(path, {})
        has_fix = bool(decision.get('fix_type'))

        if has_fix and not st.session_state.br_show_approved:
            continue
        if not has_fix and not st.session_state.br_show_pending:
            continue

        filtered_paths.append(path)

    if not filtered_paths:
        st.info("No items match your filters")
        return

    # Apply sorting
    if sort_option == "Backlinks ↓":
        filtered_paths.sort(key=lambda p: grouped_pages[p]['count'], reverse=True)
    else:  # Path A-Z
        filtered_paths.sort()

    # Pagination
    total = len(filtered_paths)
    per_page = st.session_state.br_per_page
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(st.session_state.br_page, total_pages - 1)

    start = page * per_page
    end = min(start + per_page, total)
    page_paths = filtered_paths[start:end]

    # Show count
    st.markdown(f"**Showing {start+1}-{end} of {total}** dead pages")

    # Column headers - 3 columns: Dead Page | Fixed Page | Set Fix
    st.markdown("""
    <div style="display: flex; background: linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 100%); border: 1px solid #99f6e4; border-radius: 8px; padding: 0.5rem 0.75rem; margin: 0.5rem 0;">
        <div style="flex: 3; font-size: 0.75rem; color: #0d9488; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Dead Page</div>
        <div style="flex: 4; font-size: 0.75rem; color: #0d9488; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Fixed Page</div>
        <div style="flex: 1.5; font-size: 0.75rem; color: #0d9488; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; text-align: center;">Set Fix</div>
    </div>
    """, unsafe_allow_html=True)

    # Render rows
    for path in page_paths:
        render_dead_page_row(path, grouped_pages[path], decisions.get(path, {}), domain, api_key)

    # Pagination controls
    if total_pages > 1:
        pcol1, pcol2, pcol3 = st.columns([1, 2, 1])
        with pcol1:
            if st.button("← Prev", disabled=page == 0, key="br_prev"):
                st.session_state.br_page = page - 1
                st.rerun()
        with pcol2:
            st.markdown(f"<div style='text-align:center; padding-top: 0.5rem;'>Page {page+1} / {total_pages}</div>", unsafe_allow_html=True)
        with pcol3:
            if st.button("Next →", disabled=page >= total_pages - 1, key="br_next"):
                st.session_state.br_page = page + 1
                st.rerun()


def render_dead_page_row(path: str, info: Dict, decision: Dict, domain: str, api_key: str):
    """Render a single dead page row: Dead Page | Fixed Page | Set Fix"""
    import html as html_module

    # Get the actual decision from session state
    actual_decision = st.session_state.br_decisions.get(path, decision)
    fix_type = actual_decision.get('fix_type')
    redirect_target = actual_decision.get('redirect_target', '')
    is_editing = st.session_state.br_editing_path == path

    full_url = f"https://{domain}{path}"

    # Build the row - 3 columns: Dead Page | Fixed Page | Set Fix
    with st.container():
        cols = st.columns([3, 4, 1.5])

        # Column 1: Dead Page
        with cols[0]:
            path_escaped = html_module.escape(path)
            st.markdown(f"<a href='{html_module.escape(full_url)}' target='_blank' style='color: #dc2626; text-decoration: none; font-size: 0.85rem; font-family: monospace; word-break: break-all;'>{path_escaped}</a>", unsafe_allow_html=True)

        # Column 2: Fixed Page (shows redirect target or status)
        with cols[1]:
            if fix_type == 'redirect' and redirect_target:
                url_escaped = html_module.escape(redirect_target)
                st.markdown(f"<a href='{url_escaped}' target='_blank' style='color: #059669; text-decoration: none; font-size: 0.85rem; word-break: break-all;'>{url_escaped}</a>", unsafe_allow_html=True)
            elif fix_type == 'ignore':
                st.markdown("<span style='color: #64748b; font-size: 0.85rem;'>⏭️ Ignored</span>", unsafe_allow_html=True)
            elif fix_type == 'restore':
                st.markdown("<span style='color: #8b5cf6; font-size: 0.85rem;'>🔙 Will Restore</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span style='color: #94a3b8;'>—</span>", unsafe_allow_html=True)

        # Column 3: Set Fix button
        with cols[2]:
            if is_editing:
                if st.button("✕ Close", key=f"br_close_{path}", use_container_width=True):
                    st.session_state.br_editing_path = None
                    st.rerun()
            else:
                if st.button("📝 Set Fix", key=f"br_edit_{path}", use_container_width=True):
                    st.session_state.br_editing_path = path
                    st.rerun()

        # Expanded edit section (if this row is being edited)
        if is_editing:
            render_inline_edit(path, info, decision, domain, api_key)


def render_inline_edit(path: str, info: Dict, decision: Dict, domain: str, api_key: str):
    """Render inline edit form for a dead page - button-based approach"""
    import html as html_module

    # Get the actual decision from session state (not the passed copy)
    decisions = st.session_state.br_decisions
    actual_decision = decisions.get(path, decision)

    # Initialize processing state for this path if needed
    processing_key = f'br_ai_processing_{path}'
    if processing_key not in st.session_state:
        st.session_state[processing_key] = False

    with st.container():
        # Context info with backlink count and top referrer details - compact layout
        referrers = info.get('referrers', [])
        if referrers:
            top_ref = referrers[0]
            ref_domain = top_ref.get('domain', '')
            ref_url = top_ref.get('url', '')
            ref_anchor = top_ref.get('anchor', '')
            ref_rank = top_ref.get('rank', 0)

            # Escape for HTML
            ref_url_escaped = html_module.escape(ref_url)
            ref_domain_escaped = html_module.escape(ref_domain)
            ref_anchor_escaped = html_module.escape(ref_anchor) if ref_anchor else 'No anchor'

            st.markdown(f"""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 0.5rem 0.75rem; margin: 0.25rem 0;">
                <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 0.35rem; font-size: 0.8rem;">
                    <span>📊 <strong>{info['count']}</strong> backlink(s)</span>
                    <span style="color: #cbd5e1;">|</span>
                    <span style="color: #475569;"><strong>Top:</strong> {ref_domain_escaped}</span>
                    <span style="background: #dbeafe; color: #1e40af; padding: 0.05rem 0.3rem; border-radius: 3px; font-size: 0.65rem; font-weight: 600;">DR {ref_rank}</span>
                    <span style="color: #cbd5e1;">|</span>
                    <span style="color: #64748b;">Anchor: "{ref_anchor_escaped}"</span>
                </div>
                <div style="font-size: 0.75rem; margin-top: 0.25rem;">
                    <a href="{ref_url_escaped}" target="_blank" style="color: #0d9488; text-decoration: none; word-break: break-all;">🔗 {ref_url_escaped}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"<span style='color: #64748b; font-size: 0.8rem;'>📊 <strong>{info['count']}</strong> backlink(s) pointing to this dead page</span>", unsafe_allow_html=True)

        # Quick action buttons row
        action_cols = st.columns([1, 1, 3])

        with action_cols[0]:
            if st.button("⏭️ Ignore", key=f"br_quick_ignore_{path}", use_container_width=True,
                        help="Skip this dead page"):
                decisions[path]['fix_type'] = 'ignore'
                decisions[path]['redirect_target'] = ''
                st.session_state.br_editing_path = None
                st.toast("✅ Ignored", icon="✅")
                st.rerun()

        with action_cols[1]:
            # AI suggestion button - shows inline key input if no API key
            if st.session_state.get(processing_key, False):
                st.spinner("🤖...")
            else:
                if api_key:
                    if st.button("🤖 Get AI", key=f"br_quick_ai_{path}", use_container_width=True,
                                help="Get AI redirect suggestion"):
                        st.session_state[processing_key] = True
                        st.rerun()
                else:
                    st.button("🤖 Get AI", key=f"br_quick_ai_{path}", use_container_width=True,
                             disabled=True, help="Add API key in Integrations first")

        # Process AI suggestion if triggered
        if st.session_state.get(processing_key, False) and api_key:
            with st.spinner("🤖 Getting AI suggestion..."):
                result = get_redirect_suggestion(
                    path, domain, info.get('anchor_texts', []), api_key
                )
                if result.get('target'):
                    decisions[path]['redirect_target'] = result['target']
                    decisions[path]['ai_suggested'] = True
                    decisions[path]['ai_notes'] = result.get('notes', '')
                    st.toast(f"🤖 AI suggests: {result['target']}", icon="🤖")
                else:
                    st.toast(f"AI couldn't find a suggestion", icon="⚠️")
                st.session_state[processing_key] = False
                st.rerun()

        # Show AI suggestion if available - compact
        if actual_decision.get('ai_suggested') and actual_decision.get('redirect_target'):
            ai_notes = actual_decision.get('ai_notes', '')
            ai_cols = st.columns([4, 1])
            with ai_cols[0]:
                st.markdown(f"""
                <div style="background: #d1fae5; border-radius: 4px; padding: 0.35rem 0.5rem; font-size: 0.8rem;">
                    🤖 <strong>AI:</strong> → <code style="background: #a7f3d0; padding: 0.1rem 0.3rem; border-radius: 3px;">{actual_decision['redirect_target']}</code>
                    {f'<span style="color: #065f46; margin-left: 0.5rem; font-size: 0.75rem;">— {ai_notes}</span>' if ai_notes else ''}
                </div>
                """, unsafe_allow_html=True)
            with ai_cols[1]:
                if st.button("✅ Accept", key=f"br_accept_ai_{path}", type="primary", use_container_width=True):
                    decisions[path]['fix_type'] = 'redirect'
                    st.session_state.br_editing_path = None
                    st.toast("✅ Approved", icon="✅")
                    st.rerun()

        # Manual redirect input - always visible
        base_url = f"https://{domain}/"
        current_value = actual_decision.get('redirect_target', '')

        st.markdown("<p style='font-size: 0.8rem; color: #475569; margin: 0.5rem 0 0.25rem 0;'><strong>301 redirect</strong> this dead page to a working URL on your site:</p>", unsafe_allow_html=True)

        input_cols = st.columns([4, 1])
        with input_cols[0]:
            new_target = st.text_input(
                "Redirect target",
                value=current_value,
                placeholder=f"{base_url}new-page-path",
                key=f"br_redirect_input_{path}",
                label_visibility="collapsed"
            )

        with input_cols[1]:
            if st.button("✓ Save", key=f"br_save_{path}", type="primary", use_container_width=True):
                if new_target and len(new_target.strip()) > 0:
                    decisions[path]['fix_type'] = 'redirect'
                    decisions[path]['redirect_target'] = new_target.strip()
                    if not actual_decision.get('ai_suggested'):
                        decisions[path]['ai_suggested'] = False
                    st.session_state.br_editing_path = None
                    st.toast("✅ Redirect set", icon="✅")
                    st.rerun()
                else:
                    st.toast("Enter a target URL", icon="⚠️")


def render_apply_section():
    """Render the apply redirects section with summary"""
    decisions = st.session_state.br_decisions
    domain = st.session_state.br_domain
    grouped_pages = st.session_state.br_grouped_pages
    counts = get_fix_counts()

    # Only show if there are redirects to apply
    if counts['redirect'] == 0:
        return

    st.markdown("---")

    # Summary of decisions
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #f0fdfa 0%, #ecfeff 100%); padding: 1rem; border-radius: 8px; border: 1px solid #99f6e4; margin-bottom: 1rem;">
        <div style="font-size: 1.1rem; font-weight: 600; color: #134e4a; margin-bottom: 0.5rem;">
            📊 Fix Summary
        </div>
        <div style="display: flex; gap: 1.5rem; flex-wrap: wrap;">
            <span style="color: #059669; font-size: 0.9rem;"><strong>{counts['redirect']}</strong> redirects to create</span>
            <span style="color: #8b5cf6; font-size: 0.9rem;"><strong>{counts['restore']}</strong> to restore</span>
            <span style="color: #64748b; font-size: 0.9rem;"><strong>{counts['ignore']}</strong> ignored</span>
            <span style="color: #94a3b8; font-size: 0.9rem;"><strong>{counts['pending']}</strong> pending</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Check capabilities
    wp_connected = st.session_state.get('wp_connected', False)
    seo_summary = st.session_state.get('seo_detection_summary', {})
    capabilities = seo_summary.get('capabilities', {})
    can_create_redirects = capabilities.get('redirects', False)

    if wp_connected and can_create_redirects:
        # Can create redirects automatically
        handler = capabilities.get('redirects_handler', 'SEO plugin')

        if st.button(
            f"🚀 Create {counts['redirect']} Redirect{'s' if counts['redirect'] != 1 else ''} via {handler}",
            type="primary",
            use_container_width=True
        ):
            create_redirects_via_plugin()

    elif wp_connected and not can_create_redirects:
        # WordPress connected but no redirect plugin
        st.warning(
            "No redirect plugin detected. Install **Rank Math** (free) or **Redirection** "
            "plugin to create redirects automatically. You can still export the redirects below."
        )

    else:
        # WordPress not connected - show info with link to integrations
        info_cols = st.columns([5, 2])
        with info_cols[0]:
            st.info(
                "Connect to WordPress to create redirects automatically. "
                "You can also export the redirects below."
            )
        with info_cols[1]:
            if st.button("⚙️ Open Integrations", use_container_width=True, key="br_open_integrations"):
                st.session_state.show_integrations = True
                st.session_state.scroll_to_integrations = True  # Flag to scroll to top
                st.rerun()

    # Export options (always available)
    st.markdown("""
    <div style="font-size: 0.9rem; font-weight: 500; color: #64748b; margin-top: 1rem; margin-bottom: 0.5rem;">
        Export Options:
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        csv_data = generate_csv_export(decisions, domain, grouped_pages)
        st.download_button(
            "📥 Export CSV",
            csv_data,
            file_name=f"{domain}_redirects.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        htaccess_data = generate_htaccess_export(decisions, domain)
        st.download_button(
            "📥 Export .htaccess",
            htaccess_data,
            file_name=f"{domain}_redirects.htaccess",
            mime="text/plain",
            use_container_width=True
        )


def create_redirects_via_plugin():
    """Create redirects using the detected SEO plugin"""
    decisions = st.session_state.br_decisions
    domain = st.session_state.br_domain
    seo_service = st.session_state.get('seo_service')

    if not seo_service:
        st.error("SEO service not available. Please reconnect to WordPress.")
        return

    # Get only redirect type decisions
    redirects_to_create = {
        path: decision for path, decision in decisions.items()
        if decision.get('fix_type') == 'redirect' and decision.get('redirect_target')
    }

    if not redirects_to_create:
        st.warning("No redirects to create.")
        return

    st.session_state.br_processing = True
    progress_bar = st.progress(0)
    status_text = st.empty()

    completed = []
    failed = []

    for i, (source_path, decision) in enumerate(redirects_to_create.items()):
        target = decision.get('redirect_target', '')
        status_text.text(f"Creating redirect: {source_path} → {target}")
        progress_bar.progress((i + 1) / len(redirects_to_create))

        # Build full URLs if needed
        if not target.startswith('http'):
            if not target.startswith('/'):
                target = '/' + target
            target_url = f"https://{domain}{target}"
        else:
            target_url = target

        try:
            result = seo_service.create_redirect(source_path, target_url, redirect_type=301)

            if result.get('success'):
                completed.append({
                    'source': source_path,
                    'target': target,
                    'handler': result.get('handler', 'Unknown')
                })
            else:
                failed.append({
                    'source': source_path,
                    'target': target,
                    'error': result.get('message', 'Unknown error')
                })
        except Exception as e:
            failed.append({
                'source': source_path,
                'target': target,
                'error': str(e)
            })

    st.session_state.br_completed_redirects = completed
    st.session_state.br_failed_redirects = failed
    st.session_state.br_workflow_complete = True
    st.session_state.br_processing = False

    progress_bar.empty()
    status_text.empty()
    st.rerun()


def render_success_state():
    """Render the success state after redirects are created"""
    completed = st.session_state.br_completed_redirects
    failed = st.session_state.br_failed_redirects
    domain = st.session_state.br_domain
    decisions = st.session_state.br_decisions
    grouped_pages = st.session_state.br_grouped_pages

    if completed:
        handler = completed[0].get('handler', 'SEO plugin') if completed else 'SEO plugin'
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); border: 2px solid #6ee7b7; border-radius: 12px; padding: 1.5rem; text-align: center; margin-bottom: 1rem;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎉</div>
            <div style="font-size: 1.25rem; font-weight: 600; color: #065f46; margin-bottom: 0.5rem;">
                Created {len(completed)} Redirect{'s' if len(completed) != 1 else ''} via {handler}
            </div>
            <div style="font-size: 0.95rem; color: #047857;">
                Your broken backlinks are now being fixed!
            </div>
        </div>
        """, unsafe_allow_html=True)

        # List created redirects
        with st.expander(f"View {len(completed)} Created Redirects", expanded=False):
            for r in completed:
                st.markdown(f"✅ `{r['source']}` → `{r['target']}`")

    if failed:
        st.error(f"⚠️ {len(failed)} redirect(s) failed to create")
        with st.expander("View Failed Redirects", expanded=True):
            for r in failed:
                st.markdown(f"❌ `{r['source']}`: {r['error']}")

    # Actions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Scan Another Domain", use_container_width=True, type="primary"):
            reset_backlink_reclaim_state()
            st.rerun()

    with col2:
        # Still offer export even after success
        csv_data = generate_csv_export(decisions, domain, grouped_pages)
        st.download_button(
            "📥 Export Results CSV",
            csv_data,
            file_name=f"{domain}_redirects_results.csv",
            mime="text/csv",
            use_container_width=True
        )


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def render_backlink_fix_workflow(
    scan_results: Optional[Dict] = None,
    domain: Optional[str] = None,
    api_key: Optional[str] = None
):
    """
    Main entry point for the backlink fix workflow.

    Can be called with scan_results to load new data, or without
    to continue an existing workflow.

    Args:
        scan_results: Optional dict with 'backlinks' list from DataForSEO
        domain: The domain being fixed
        api_key: API key for AI suggestions (defaults to AGENT_MODE_API_KEY)
    """
    # Initialize state
    init_backlink_reclaim_state()

    # Only load scan results if we don't already have decisions initialized
    # This prevents wiping user changes on every rerun
    if scan_results and domain and not st.session_state.br_decisions:
        load_scan_results(scan_results, domain)

    # Use provided API key or default
    if not api_key:
        api_key = AGENT_MODE_API_KEY

    # Check if we have data to work with
    if not st.session_state.br_grouped_pages:
        st.info("No scan results loaded. Run a backlink scan to get started.")
        return

    # Check if workflow is complete (redirects created)
    if st.session_state.br_workflow_complete:
        render_success_state()
        return

    # Render the workflow - matches Broken Links style
    render_metrics()
    render_spreadsheet(api_key)
    render_apply_section()
