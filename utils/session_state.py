"""
Session state initialization for Screaming Fixes.
Centralizes all session state defaults in one place.
"""

import streamlit as st

from config import AGENT_MODE_FREE_SUGGESTIONS


def init_session_state():
    """Initialize all session state variables with defaults"""
    defaults = {
        # Task type management
        'task_type': None,  # 'broken_links', 'redirect_chains', or 'image_alt_text'
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
        'rc_show_approve_warning': False,  # Warning modal for 302s

        # Image Alt Text data
        'iat_df': None,  # Raw dataframe
        'iat_domain': None,
        'iat_images': {},  # Grouped image data by image URL
        'iat_decisions': {},
        'iat_excluded_count': 0,  # Count of filtered out images

        # Image Alt Text filters
        'iat_show_approved': True,
        'iat_show_pending': True,
        'iat_page': 0,
        'iat_editing_url': None,

        # WordPress connection (shared)
        'wp_connected': False,
        'wp_client': None,
        'wp_preview_results': None,
        'wp_execute_results': None,
        'wp_preview_done': False,
        'wp_was_test_run': False,  # Track if last execution was a test run
        'selected_mode': 'quick_start',  # 'quick_start' or 'full'

        # AI Configuration (future-proofed for multiple providers)
        'ai_config': {
            'provider': 'claude',  # 'claude', 'grok', 'openai', etc.
            'api_key': '',
            'model': 'claude-sonnet-4-20250514'
        },
        'anthropic_key': '',  # Legacy - kept for backwards compatibility
        'ai_suggestions_remaining': AGENT_MODE_FREE_SUGGESTIONS,  # Free suggestions in Quick Start Mode

        # Broken Links UI state
        'page': 0,
        'per_page': 10,
        'filter_internal': True,
        'filter_external': True,
        'filter_status': None,  # None = All, or specific status code like 404
        'show_approved': True,
        'show_pending': True,
        'bulk_action': None,  # For bulk action confirmation
        'sort_by': 'impact',  # Sort option: impact, status_code, internal_first
        'editing_url': None,  # Currently editing URL (for inline edit form)

        # Post ID tracking (shared)
        'has_post_ids': False,  # CSV included post_id column or Post ID file uploaded
        'post_id_file_uploaded': False,  # Separate Post ID file was uploaded
        'post_id_file_count': 0,  # Count from uploaded Post ID file
        'post_id_matched_count': 0,  # How many report URLs matched with Post IDs
        'post_id_unmatched_urls': [],  # URLs that didn't match (for display)
        'source_pages_count': 0,  # Total unique source pages
        'post_id_check_done': False,  # Sample check completed
        'post_id_check_passed': False,  # Sample check found Post IDs
        'post_id_cache': {},  # Cache of URL -> Post ID (found or manual)
        'full_mode_available': False,  # Post IDs available for unlimited fixes

        # Integrations panel state
        'show_integrations': False,  # Whether integrations panel is expanded
        'scroll_to_integrations': False,  # Scroll to integrations section

        # Bulk AI analysis state
        'show_bulk_ai_modal': False,
        'bulk_ai_running': False,
        'bulk_ai_progress': 0,
        'bulk_ai_total': 0,
        'bulk_ai_urls_to_process': [],
        'bulk_ai_analyzed_urls': set(),
        'bulk_ai_results_summary': {'replace': 0, 'remove': 0, 'error': 0},
        'bulk_ai_start_time': 0,
        'bulk_ai_just_completed': False,
        'bulk_ai_recent_results': [],  # Recent results for display
        'bulk_ai_paused_until': 0,  # Timestamp for rate limit pause
        'bulk_ai_pause_reason': '',  # Reason for pause
        'bulk_ai_error_state': None,  # Current error state dict
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
