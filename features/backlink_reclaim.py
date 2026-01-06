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
        'br_suggested_redirects': {},  # {"/dead-path/": {"target": "/suggested/", "notes": "..."}}
        'br_approved_redirects': {},  # {"/dead-path/": "/approved-target/"}
        'br_redirect_inputs': {},  # {"/dead-path/": "current input value"}
        'br_processing': False,  # Loading state
        'br_processing_item': None,  # Currently processing item
        'br_completed_redirects': [],  # List of successfully created redirects
        'br_failed_redirects': [],  # List of failed redirect attempts
        'br_workflow_complete': False,  # Whether redirects have been created
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def reset_backlink_reclaim_state():
    """Reset all backlink reclaim state variables"""
    keys_to_reset = [
        'br_scan_results', 'br_domain', 'br_grouped_pages',
        'br_suggested_redirects', 'br_approved_redirects', 'br_redirect_inputs',
        'br_processing', 'br_processing_item', 'br_completed_redirects',
        'br_failed_redirects', 'br_workflow_complete'
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
    backlinks = scan_results.get('backlinks', [])

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

    # Initialize redirect inputs with empty values
    st.session_state.br_redirect_inputs = {path: '' for path in sorted_grouped.keys()}


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

def generate_csv_export(approved_redirects: Dict[str, str], domain: str, grouped_pages: Dict) -> str:
    """Generate CSV export of approved redirects"""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(['Source URL', 'Target URL', 'Redirect Type', 'Backlink Count', 'Top Referrer'])

    for source_path, target in approved_redirects.items():
        source_url = f"https://{domain}{source_path}"

        # Build target URL
        if target.startswith('http'):
            target_url = target
        elif target.startswith('/'):
            target_url = f"https://{domain}{target}"
        else:
            target_url = f"https://{domain}/{target}"

        # Get referrer info
        page_info = grouped_pages.get(source_path, {})
        backlink_count = page_info.get('count', 0)
        referrers = page_info.get('referrers', [])
        top_referrer = referrers[0]['domain'] if referrers else ''

        writer.writerow([source_url, target_url, '301', backlink_count, top_referrer])

    return output.getvalue()


def generate_htaccess_export(approved_redirects: Dict[str, str], domain: str) -> str:
    """Generate .htaccess redirect rules"""
    lines = [
        "# Redirects generated by Screaming Fixes",
        f"# Domain: {domain}",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "# 301 Redirects",
    ]

    for source_path, target in approved_redirects.items():
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

def render_status_header():
    """Render the header section with status indicators"""
    domain = st.session_state.br_domain
    grouped_pages = st.session_state.br_grouped_pages
    total_backlinks = sum(p['count'] for p in grouped_pages.values())

    # Header
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #f0fdfa 0%, #ecfeff 100%); padding: 1.5rem; border-radius: 12px; border: 1px solid #99f6e4; margin-bottom: 1.5rem;">
        <h2 style="margin: 0 0 0.5rem 0; color: #134e4a; font-size: 1.5rem;">
            Fix {len(grouped_pages)} Broken Pages with {total_backlinks} Backlinks
        </h2>
        <p style="margin: 0; color: #0d9488; font-size: 1rem;">
            Domain: <strong>{domain}</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Status indicators
    col1, col2 = st.columns(2)

    with col1:
        # WordPress connection status
        wp_connected = st.session_state.get('wp_connected', False)
        if wp_connected:
            st.markdown("""
            <div style="background: #d1fae5; border: 1px solid #6ee7b7; border-radius: 8px; padding: 0.5rem 0.75rem;">
                <span style="color: #065f46; font-size: 0.85rem;">✅ WordPress Connected</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: #fef3c7; border: 1px solid #fcd34d; border-radius: 8px; padding: 0.5rem 0.75rem;">
                <span style="color: #92400e; font-size: 0.85rem;">⚠️ WordPress Not Connected</span>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        # SEO plugin status
        seo_summary = st.session_state.get('seo_detection_summary', {})
        capabilities = seo_summary.get('capabilities', {})
        redirects_available = capabilities.get('redirects', False)
        redirects_handler = capabilities.get('redirects_handler')

        if redirects_available and redirects_handler:
            st.markdown(f"""
            <div style="background: #d1fae5; border: 1px solid #6ee7b7; border-radius: 8px; padding: 0.5rem 0.75rem;">
                <span style="color: #065f46; font-size: 0.85rem;">✅ Redirects via {redirects_handler}</span>
            </div>
            """, unsafe_allow_html=True)
        elif st.session_state.get('wp_connected', False):
            st.markdown("""
            <div style="background: #fef3c7; border: 1px solid #fcd34d; border-radius: 8px; padding: 0.5rem 0.75rem;">
                <span style="color: #92400e; font-size: 0.85rem;">⚠️ No redirect plugin detected</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.5rem 0.75rem;">
                <span style="color: #64748b; font-size: 0.85rem;">🔌 Connect WordPress for auto-redirects</span>
            </div>
            """, unsafe_allow_html=True)


def render_batch_actions(api_key: str):
    """Render batch action buttons"""
    grouped_pages = st.session_state.br_grouped_pages
    suggested = st.session_state.br_suggested_redirects
    inputs = st.session_state.br_redirect_inputs

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        # Count how many still need suggestions
        needs_suggestion = sum(1 for path in grouped_pages.keys()
                               if path not in suggested or not suggested[path].get('target'))

        if st.button(
            f"🤖 Get AI Suggestions ({needs_suggestion})",
            disabled=st.session_state.br_processing or needs_suggestion == 0,
            use_container_width=True,
            type="primary" if needs_suggestion > 0 else "secondary"
        ):
            get_all_suggestions(api_key)

    with col2:
        # Count how many have targets filled in but not approved
        ready_to_approve = sum(1 for path, target in inputs.items()
                               if target and path not in st.session_state.br_approved_redirects)

        if st.button(
            f"✅ Approve All with Targets ({ready_to_approve})",
            disabled=ready_to_approve == 0,
            use_container_width=True
        ):
            approve_all_with_targets()

    with col3:
        approved_count = len(st.session_state.br_approved_redirects)
        st.markdown(f"""
        <div style="text-align: center; padding: 0.5rem;">
            <div style="font-size: 1.5rem; font-weight: 600; color: #0d9488;">{approved_count}</div>
            <div style="font-size: 0.75rem; color: #64748b;">Approved</div>
        </div>
        """, unsafe_allow_html=True)


def get_all_suggestions(api_key: str):
    """Get AI suggestions for all pages that don't have one"""
    st.session_state.br_processing = True
    domain = st.session_state.br_domain
    grouped_pages = st.session_state.br_grouped_pages
    suggested = st.session_state.br_suggested_redirects

    progress_bar = st.progress(0)
    status_text = st.empty()

    paths_needing_suggestions = [
        path for path in grouped_pages.keys()
        if path not in suggested or not suggested[path].get('target')
    ]

    for i, path in enumerate(paths_needing_suggestions):
        st.session_state.br_processing_item = path
        status_text.text(f"Getting suggestion for {path}...")
        progress_bar.progress((i + 1) / len(paths_needing_suggestions))

        page_info = grouped_pages[path]
        anchor_texts = page_info.get('anchor_texts', [])

        result = get_redirect_suggestion(path, domain, anchor_texts, api_key)

        if result.get('target'):
            st.session_state.br_suggested_redirects[path] = result
            st.session_state.br_redirect_inputs[path] = result['target']

    st.session_state.br_processing = False
    st.session_state.br_processing_item = None
    progress_bar.empty()
    status_text.empty()
    st.rerun()


def approve_all_with_targets():
    """Approve all redirects that have a target filled in"""
    inputs = st.session_state.br_redirect_inputs

    for path, target in inputs.items():
        if target and target.strip():
            st.session_state.br_approved_redirects[path] = target.strip()

    st.rerun()


def render_results_table(api_key: str):
    """Render the results table with redirect inputs"""
    grouped_pages = st.session_state.br_grouped_pages
    suggested = st.session_state.br_suggested_redirects
    approved = st.session_state.br_approved_redirects
    inputs = st.session_state.br_redirect_inputs
    domain = st.session_state.br_domain

    st.markdown("""
    <div style="font-size: 0.85rem; font-weight: 600; color: #134e4a; margin-bottom: 0.75rem;">
        Dead Pages to Fix:
    </div>
    """, unsafe_allow_html=True)

    for path, info in grouped_pages.items():
        is_approved = path in approved
        has_suggestion = path in suggested and suggested[path].get('target')

        # Row container styling
        bg_color = "#f0fdfa" if is_approved else "#ffffff"
        border_color = "#6ee7b7" if is_approved else "#e2e8f0"

        with st.container():
            st.markdown(f"""
            <div style="background: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem;">
            """, unsafe_allow_html=True)

            cols = st.columns([3, 1, 2, 3, 1])

            # Dead Page column
            with cols[0]:
                st.markdown(f"""
                <div style="font-family: monospace; font-size: 0.8rem; color: #dc2626; word-break: break-all;">
                    {path}
                </div>
                """, unsafe_allow_html=True)

            # Backlinks count column
            with cols[1]:
                st.markdown(f"""
                <div style="text-align: center;">
                    <span style="background: #fee2e2; color: #dc2626; padding: 0.15rem 0.5rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">
                        {info['count']} links
                    </span>
                </div>
                """, unsafe_allow_html=True)

            # Top Referrer column
            with cols[2]:
                referrers = info.get('referrers', [])
                if referrers:
                    top_ref = referrers[0]
                    st.markdown(f"""
                    <div style="font-size: 0.75rem; color: #64748b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        {top_ref['domain']}<br>
                        <span style="color: #94a3b8;">DR: {top_ref.get('rank', 0)}</span>
                    </div>
                    """, unsafe_allow_html=True)

            # Redirect To input column
            with cols[3]:
                current_value = inputs.get(path, '')
                suggestion_note = suggested.get(path, {}).get('notes', '')

                new_value = st.text_input(
                    "Redirect to",
                    value=current_value,
                    key=f"redirect_input_{path}",
                    placeholder="/new-path/",
                    label_visibility="collapsed",
                    disabled=is_approved
                )

                # Update input value
                if new_value != current_value:
                    st.session_state.br_redirect_inputs[path] = new_value

                if suggestion_note and has_suggestion:
                    st.caption(f"💡 {suggestion_note[:60]}...")

            # Actions column
            with cols[4]:
                if is_approved:
                    if st.button("↩️", key=f"unapprove_{path}", help="Unapprove"):
                        del st.session_state.br_approved_redirects[path]
                        st.rerun()
                else:
                    action_cols = st.columns(2)
                    with action_cols[0]:
                        if st.button("🤖", key=f"suggest_{path}", help="Get AI suggestion",
                                     disabled=st.session_state.br_processing):
                            st.session_state.br_processing = True
                            result = get_redirect_suggestion(
                                path, domain, info.get('anchor_texts', []), api_key
                            )
                            if result.get('target'):
                                st.session_state.br_suggested_redirects[path] = result
                                st.session_state.br_redirect_inputs[path] = result['target']
                            st.session_state.br_processing = False
                            st.rerun()

                    with action_cols[1]:
                        current_input = inputs.get(path, '')
                        if st.button("✅", key=f"approve_{path}", help="Approve",
                                     disabled=not current_input):
                            st.session_state.br_approved_redirects[path] = current_input
                            st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)


def render_apply_section():
    """Render the apply redirects section"""
    approved = st.session_state.br_approved_redirects
    domain = st.session_state.br_domain
    grouped_pages = st.session_state.br_grouped_pages

    if not approved:
        return

    st.markdown("---")
    st.markdown(f"""
    <div style="font-size: 1.1rem; font-weight: 600; color: #134e4a; margin-bottom: 0.75rem;">
        🚀 Apply {len(approved)} Redirect{'s' if len(approved) != 1 else ''}
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
            f"🚀 Create {len(approved)} Redirects via {handler}",
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
        # WordPress not connected
        st.info(
            "Connect to WordPress in the integrations panel to create redirects automatically. "
            "You can also export the redirects below."
        )

    # Export options (always available)
    st.markdown("""
    <div style="font-size: 0.9rem; font-weight: 500; color: #64748b; margin-top: 1rem; margin-bottom: 0.5rem;">
        Export Options:
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        csv_data = generate_csv_export(approved, domain, grouped_pages)
        st.download_button(
            "📥 Export CSV",
            csv_data,
            file_name=f"{domain}_redirects.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        htaccess_data = generate_htaccess_export(approved, domain)
        st.download_button(
            "📥 Export .htaccess",
            htaccess_data,
            file_name=f"{domain}_redirects.htaccess",
            mime="text/plain",
            use_container_width=True
        )


def create_redirects_via_plugin():
    """Create redirects using the detected SEO plugin"""
    approved = st.session_state.br_approved_redirects
    domain = st.session_state.br_domain
    seo_service = st.session_state.get('seo_service')

    if not seo_service:
        st.error("SEO service not available. Please reconnect to WordPress.")
        return

    st.session_state.br_processing = True
    progress_bar = st.progress(0)
    status_text = st.empty()

    completed = []
    failed = []

    for i, (source_path, target) in enumerate(approved.items()):
        status_text.text(f"Creating redirect: {source_path} → {target}")
        progress_bar.progress((i + 1) / len(approved))

        # Build full URLs if needed
        if not target.startswith('http'):
            if not target.startswith('/'):
                target = '/' + target
            target_url = f"https://{domain}{target}"
        else:
            target_url = target

        source_url = f"https://{domain}{source_path}"

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
        approved = st.session_state.br_approved_redirects
        grouped_pages = st.session_state.br_grouped_pages
        csv_data = generate_csv_export(approved, domain, grouped_pages)
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

    # Load new scan results if provided
    if scan_results and domain:
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

    # Render the workflow
    render_status_header()
    render_batch_actions(api_key)

    st.markdown("---")

    render_results_table(api_key)
    render_apply_section()
