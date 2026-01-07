"""
Sidebar/Integrations Panel Components for Screaming Fixes.
Handles the integrations setup panel with progressive steps.
"""

from typing import Dict, Callable, Optional, Any

import streamlit as st

# Optional WordPress client import
try:
    from wordpress_client import WordPressClient
    WP_AVAILABLE = True
except ImportError:
    WP_AVAILABLE = False

# Optional SEO service import
try:
    from services.wordpress import SEOService, PluginDetector
    SEO_SERVICE_AVAILABLE = True
except ImportError:
    SEO_SERVICE_AVAILABLE = False


def run_plugin_detection() -> Optional[Dict[str, Any]]:
    """
    Run SEO plugin detection on the connected WordPress site.

    Returns:
        Detection summary dict or None if detection fails
    """
    if not SEO_SERVICE_AVAILABLE:
        return None

    if not st.session_state.get('wp_connected') or not st.session_state.get('wp_client'):
        return None

    try:
        # Check if we've already detected plugins for this session
        if 'seo_detection_summary' in st.session_state:
            return st.session_state.seo_detection_summary

        # Run detection
        seo_service = SEOService(st.session_state.wp_client)
        summary = seo_service.get_summary()

        # Cache the results and service
        st.session_state.seo_detection_summary = summary
        st.session_state.seo_service = seo_service

        return summary
    except Exception as e:
        # Silent fail - don't break the UI
        return None


def render_detected_plugins():
    """
    Render the detected SEO plugins section.

    Shows which plugins were found and what capabilities are available.
    """
    if not st.session_state.get('wp_connected'):
        return

    summary = run_plugin_detection()

    if not summary:
        return

    plugins = summary.get('plugins', [])
    capabilities = summary.get('capabilities', {})

    if not plugins:
        # No SEO plugins detected - show recommendation
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border: 1px solid #fcd34d; border-radius: 8px; padding: 0.75rem 1rem; margin-top: 0.5rem; margin-bottom: 0.5rem;">
            <div style="font-size: 0.9rem; color: #92400e; font-weight: 500;">
                ⚠️ No SEO plugins detected
            </div>
            <div style="font-size: 0.8rem; color: #a16207; margin-top: 0.25rem;">
                Install <strong>Rank Math</strong> or <strong>Redirection</strong> to enable automatic redirect creation for broken links.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Show detected plugins
    st.markdown("""
    <div style="font-size: 0.85rem; font-weight: 600; color: #134e4a; margin-top: 0.75rem; margin-bottom: 0.5rem;">
        Detected SEO Plugins:
    </div>
    """, unsafe_allow_html=True)

    for plugin in plugins:
        name = plugin.get('name', 'Unknown')
        is_premium = plugin.get('is_premium', False)
        can_redirects = plugin.get('can_redirects', False)
        can_meta = plugin.get('can_meta', False)

        premium_badge = '<span style="background: #dbeafe; color: #1d4ed8; padding: 0.1rem 0.35rem; border-radius: 4px; font-size: 0.65rem; margin-left: 0.35rem;">PRO</span>' if is_premium else ''

        features = []
        if can_redirects:
            features.append("🔀 Redirects")
        if can_meta:
            features.append("🏷️ Meta Tags")

        features_text = " • ".join(features) if features else "Detection only"

        st.markdown(f"""
        <div style="background: #f0fdfa; border: 1px solid #a7f3d0; border-radius: 6px; padding: 0.5rem 0.75rem; margin-bottom: 0.35rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.85rem; font-weight: 500; color: #065f46;">
                    ✅ {name}{premium_badge}
                </span>
            </div>
            <div style="font-size: 0.75rem; color: #047857; margin-top: 0.2rem;">
                {features_text}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Show capability summary
    redirects_available = capabilities.get('redirects', False)
    redirects_handler = capabilities.get('redirects_handler')
    meta_available = capabilities.get('meta_tags', False)
    meta_handler = capabilities.get('meta_handler')

    st.markdown("""
    <div style="font-size: 0.85rem; font-weight: 600; color: #134e4a; margin-top: 0.75rem; margin-bottom: 0.35rem;">
        Available Features:
    </div>
    """, unsafe_allow_html=True)

    # Redirects capability
    if redirects_available:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
            <span style="color: #059669;">✅</span>
            <span style="font-size: 0.8rem; color: #065f46;">Redirects</span>
            <span style="font-size: 0.7rem; color: #64748b;">via {redirects_handler}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
            <span style="color: #dc2626;">❌</span>
            <span style="font-size: 0.8rem; color: #64748b;">Redirects</span>
            <span style="font-size: 0.7rem; color: #94a3b8;">Install Rank Math or Redirection</span>
        </div>
        """, unsafe_allow_html=True)

    # Meta tags capability
    if meta_available:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
            <span style="color: #059669;">✅</span>
            <span style="font-size: 0.8rem; color: #065f46;">Meta Tags</span>
            <span style="font-size: 0.7rem; color: #64748b;">via {meta_handler}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
            <span style="color: #dc2626;">❌</span>
            <span style="font-size: 0.8rem; color: #64748b;">Meta Tags</span>
            <span style="font-size: 0.7rem; color: #94a3b8;">Install Rank Math or Yoast</span>
        </div>
        """, unsafe_allow_html=True)


def get_integration_status() -> Dict[str, any]:
    """Get the status of all integrations"""
    has_post_ids = st.session_state.post_id_file_uploaded or st.session_state.has_post_ids
    has_ai_key = bool(st.session_state.ai_config.get('api_key') or st.session_state.anthropic_key)
    has_wordpress = st.session_state.wp_connected

    return {
        'post_ids': has_post_ids,
        'ai_key': has_ai_key,
        'wordpress': has_wordpress,
        'all_connected': has_post_ids and has_ai_key and has_wordpress,
        'count_connected': sum([has_post_ids, has_ai_key, has_wordpress])
    }


def render_feature_cards():
    """Render the What You Can Fix feature cards section"""
    st.markdown("""
    <h3 style="text-align: center; color: #134e4a; font-weight: 600; margin-bottom: 1.25rem; font-size: 1.35rem;">
        What You Can Fix
    </h3>
    """, unsafe_allow_html=True)

    # Get integration status
    status = get_integration_status()

    # Determine card states
    # Broken Links and Redirect Chains are always ready (they work without full integration)
    # Image Alt Text requires all 3 integrations
    broken_links_ready = True
    redirect_chains_ready = True
    image_alt_ready = status['all_connected']

    col1, col2, col3 = st.columns(3)

    with col1:
        card_class = "ready" if broken_links_ready else "locked"
        status_class = "ready" if broken_links_ready else "locked"
        status_text = "✅ Ready" if broken_links_ready else "🔒 Needs Setup"

        st.markdown(f"""
        <div class="feature-card {card_class}">
            <div class="feature-card-icon">🔗</div>
            <div class="feature-card-title">Broken Links</div>
            <div class="feature-card-desc">Find and fix 404s across your entire site</div>
            <div class="feature-card-status {status_class}">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        card_class = "ready" if redirect_chains_ready else "locked"
        status_class = "ready" if redirect_chains_ready else "locked"
        status_text = "✅ Ready" if redirect_chains_ready else "🔒 Needs Setup"

        st.markdown(f"""
        <div class="feature-card {card_class}">
            <div class="feature-card-icon">🔄</div>
            <div class="feature-card-title">Redirect Chains</div>
            <div class="feature-card-desc">Update outdated URLs to final destinations</div>
            <div class="feature-card-status {status_class}">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        card_class = "ready" if image_alt_ready else "locked"
        status_class = "ready" if image_alt_ready else "locked"
        status_text = "✅ Ready" if image_alt_ready else "🔒 Needs Setup"

        if image_alt_ready:
            st.markdown(f"""
            <div class="feature-card {card_class}">
                <div class="feature-card-icon">🖼️</div>
                <div class="feature-card-title">Image Alt Text</div>
                <div class="feature-card-desc">Add missing descriptions with AI</div>
                <div class="feature-card-status {status_class}">{status_text}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Show locked card
            st.markdown(f"""
            <div class="feature-card {card_class}">
                <div class="feature-card-icon">🖼️</div>
                <div class="feature-card-title">Image Alt Text</div>
                <div class="feature-card-desc">Add missing descriptions with AI</div>
                <div class="feature-card-status {status_class}">{status_text}</div>
            </div>
            """, unsafe_allow_html=True)

    # Unlock message
    if not status['all_connected']:
        missing = []
        if not status['post_ids']:
            missing.append("Post IDs")
        if not status['ai_key']:
            missing.append("AI API Key")
        if not status['wordpress']:
            missing.append("WordPress")

        st.markdown(f"""
        <div style="text-align: center; margin-top: 1.25rem; padding: 1rem; background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); border-radius: 10px; border: 1px solid #fcd34d;">
            <div style="font-size: 1rem; color: #92400e; font-weight: 500;">
                ⚡ <strong>Unlock all features for FREE</strong>
            </div>
            <div style="font-size: 0.9rem; color: #a16207; margin-top: 0.35rem;">
                Complete {3 - status['count_connected']} more integration{'s' if 3 - status['count_connected'] > 1 else ''} to fix everything automatically
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Toggle button
        btn_label = "▼ Hide Integrations Setup" if st.session_state.show_integrations else "▶ Complete Integrations Setup"
        if st.button(btn_label, key="toggle_integrations_btn", type="primary", use_container_width=True):
            st.session_state.show_integrations = not st.session_state.show_integrations
            st.rerun()
    else:
        st.markdown("""
        <div style="text-align: center; margin-top: 1.25rem; padding: 1rem; background: linear-gradient(135deg, #f0fdfa 0%, #d1fae5 100%); border-radius: 10px; border: 1px solid #6ee7b7;">
            <div style="font-size: 1rem; color: #065f46; font-weight: 500;">
                ✅ <strong>All integrations connected!</strong> You have full access to all features.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Still allow toggling to view/manage integrations
        btn_label = "▼ Hide Integrations" if st.session_state.show_integrations else "⚙️ Manage Integrations"
        if st.button(btn_label, key="toggle_integrations_btn_connected", use_container_width=True):
            st.session_state.show_integrations = not st.session_state.show_integrations
            st.rerun()


def render_integrations_panel(process_post_id_upload: Callable):
    """
    Render the integrations setup panel with progressive steps.

    Args:
        process_post_id_upload: Callback function to process Post ID uploads
    """
    status = get_integration_status()

    # Add anchor for scroll-to functionality
    st.markdown('<div id="integrations-panel"></div>', unsafe_allow_html=True)

    # Check if we need to scroll to this section
    if st.session_state.get('scroll_to_integrations', False):
        st.markdown("""
        <script>
            // Scroll to integrations panel
            const element = document.getElementById('integrations-panel');
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        </script>
        """, unsafe_allow_html=True)
        # Clear the flag
        st.session_state.scroll_to_integrations = False

    # Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f0fdfa 0%, #ecfeff 100%); padding: 1.25rem 1.5rem; border-radius: 12px; border: 1px solid #99f6e4; margin-top: 1rem; margin-bottom: 1rem;">
        <div style="font-size: 1.25rem; font-weight: 600; color: #134e4a; margin-bottom: 0.5rem;">
            ⚙️ Complete Your Integrations
        </div>
        <div style="font-size: 0.95rem; color: #0d9488; line-height: 1.5;">
            Set this up one time and you'll unlock the full power of Screaming Fixes.
            Each integration takes just a few minutes — and they're all <strong>completely free</strong>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Progress bar
    completed = status['count_connected']
    progress_pct = (completed / 3) * 100

    st.markdown(f"""
    <div style="margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
            <span style="font-size: 0.9rem; font-weight: 500; color: #134e4a;">Progress</span>
            <span style="font-size: 0.9rem; color: #0d9488; font-weight: 600;">{completed} of 3 complete</span>
        </div>
        <div style="background: #e2e8f0; border-radius: 10px; height: 10px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, #14b8a6 0%, #0d9488 100%); height: 100%; width: {progress_pct}%; border-radius: 10px; transition: width 0.3s ease;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ===========================================
    # STEP 1: Post IDs
    # ===========================================
    step1_complete = status['post_ids']
    step1_status_icon = "✅" if step1_complete else "1️⃣"
    step1_border_color = "#6ee7b7" if step1_complete else "#fcd34d"
    step1_bg = "linear-gradient(135deg, #f0fdfa 0%, #d1fae5 100%)" if step1_complete else "linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)"
    step1_header_color = "#065f46" if step1_complete else "#92400e"
    step1_complete_badge = '<span style="background: #d1fae5; color: #065f46; padding: 0.15rem 0.5rem; border-radius: 12px; font-size: 0.75rem; margin-left: 0.5rem;">✓ Complete</span>' if step1_complete else ''

    post_id_count = len(st.session_state.post_id_cache)

    st.markdown(f"""
    <div style="background: {step1_bg}; border: 2px solid {step1_border_color}; border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span style="font-size: 1.5rem;">{step1_status_icon}</span>
            <div>
                <div style="font-size: 1.1rem; font-weight: 600; color: {step1_header_color};">
                    Step 1: Upload Post IDs {step1_complete_badge}
                </div>
                <div style="font-size: 0.85rem; color: #64748b; margin-top: 0.25rem;">Map your URLs to WordPress Post IDs</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not step1_complete:
        st.markdown("""
        <div style="background: #f8fafc; border-radius: 8px; padding: 1rem; margin-top: -0.5rem; margin-bottom: 1rem; border: 1px solid #e2e8f0;">
            <div style="font-size: 0.9rem; color: #475569; line-height: 1.6;">
                <strong>Why this matters:</strong> WordPress stores every page with a numeric Post ID (like <code>6125</code>),
                but your URLs only show the slug (like <code>/how-to-start-a-food-truck/</code>).
                To edit content via the API, we need this mapping.<br><br>
                <strong>How to get it:</strong> Set up a one-time Custom Extraction in Screaming Frog to pull Post IDs during your crawl.
                Takes ~3 minutes to configure, then you'll have it for every future crawl.
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📋 Step-by-step instructions", expanded=False):
            st.markdown("""
            1. In Screaming Frog, go to **Configuration → Custom → Extraction**
            2. Click **Add** and set:
               - **Name:** `post_id`
               - **Type:** Regex
               - **Regex:** `<link[^>]+rel=['"]shortlink['"][^>]+href=['"][^'"]*\\?p=(\\d+)`
            3. Click **OK** and re-crawl your site
            4. Go to **Bulk Export → Custom Extraction → post_id**
            5. Upload that CSV file below

            [📖 Full Setup Guide with Screenshots](https://github.com/backofnapkin/screaming-fixes/blob/main/POST_ID_SETUP.md) ・ [🔧 Can't find Post IDs?](https://github.com/backofnapkin/screaming-fixes/blob/main/CUSTOM_POST_ID_GUIDE.md)
            """)

        post_id_file = st.file_uploader(
            "Upload Post IDs CSV",
            type=['csv'],
            key="integration_post_id_uploader",
            label_visibility="collapsed"
        )

        if post_id_file:
            if process_post_id_upload(post_id_file):
                st.success(f"✅ Post IDs uploaded! {len(st.session_state.post_id_cache)} URLs mapped.")
                st.rerun()
    else:
        st.markdown(f"""
        <div style="background: #f0fdfa; border-radius: 8px; padding: 0.75rem 1rem; margin-top: -0.5rem; margin-bottom: 1rem; border: 1px solid #a7f3d0;">
            <span style="color: #065f46;">✅ <strong>{post_id_count} URLs mapped</strong> — Post IDs ready to use</span>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🗑️ Clear Post IDs", key="clear_post_ids_integration"):
            st.session_state.post_id_cache = {}
            st.session_state.post_id_file_uploaded = False
            st.session_state.post_id_file_count = 0
            st.session_state.has_post_ids = False
            st.session_state.selected_mode = 'quick_start'
            st.rerun()

    # ===========================================
    # STEP 2: AI API Key
    # ===========================================
    step2_complete = status['ai_key']
    step2_status_icon = "✅" if step2_complete else "2️⃣"
    step2_border_color = "#6ee7b7" if step2_complete else ("#fcd34d" if status['post_ids'] else "#e2e8f0")
    step2_bg = "linear-gradient(135deg, #f0fdfa 0%, #d1fae5 100%)" if step2_complete else ("linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)" if status['post_ids'] else "linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)")
    step2_header_color = "#065f46" if step2_complete else ("#92400e" if status['post_ids'] else "#64748b")
    step2_opacity = "1" if status['post_ids'] or step2_complete else "0.7"
    step2_complete_badge = '<span style="background: #d1fae5; color: #065f46; padding: 0.15rem 0.5rem; border-radius: 12px; font-size: 0.75rem; margin-left: 0.5rem;">✓ Complete</span>' if step2_complete else ''

    current_provider = st.session_state.ai_config.get('provider', 'claude')

    st.markdown(f"""
    <div style="background: {step2_bg}; border: 2px solid {step2_border_color}; border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem; opacity: {step2_opacity};">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span style="font-size: 1.5rem;">{step2_status_icon}</span>
            <div>
                <div style="font-size: 1.1rem; font-weight: 600; color: {step2_header_color};">
                    Step 2: Add Your AI API Key {step2_complete_badge}
                </div>
                <div style="font-size: 0.85rem; color: #64748b; margin-top: 0.25rem;">Enable AI-powered fix suggestions</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not step2_complete:
        st.markdown("""
        <div style="background: #f8fafc; border-radius: 8px; padding: 1rem; margin-top: -0.5rem; margin-bottom: 1rem; border: 1px solid #e2e8f0;">
            <div style="font-size: 0.9rem; color: #475569; line-height: 1.6;">
                <strong>Why this matters:</strong> AI can analyze your broken links, search for alternatives,
                and suggest the best fix — saving you hours of manual research. It can also analyze images
                and write descriptive alt text automatically.<br><br>
                <strong>Cost:</strong> Free credits to start, then ~$0.01 per suggestion. No monthly fees.
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📋 How to get your Claude API key", expanded=False):
            st.markdown("""
            1. Go to [console.anthropic.com](https://console.anthropic.com) and create an account
            2. Add a payment method in **Settings → Billing** (required, but you get free credits)
            3. Set a **Usage Limit** (e.g., $5/month) to control spending
            4. Go to **API Keys** → **Create Key**
            5. Name it `Screaming Fixes` and click **Create**
            6. **Copy the key immediately** — you won't see it again!

            Your key looks like: `sk-ant-api03-aBcDeF123...` (about 100+ characters)

            [📖 Full Setup Guide](https://github.com/backofnapkin/screaming-fixes/blob/main/CLAUDE_API_SETUP.md)
            """)

        # Provider selector (future-proofed)
        st.markdown("**Select AI Provider:**")
        provider_options = ["Claude (Recommended)", "More providers coming soon..."]
        selected_provider = st.selectbox(
            "Select AI Provider",
            provider_options,
            index=0,
            key="ai_provider_select",
            label_visibility="collapsed"
        )

        api_key_input = st.text_input(
            "Paste your API key",
            type="password",
            placeholder="sk-ant-api03-...",
            key="integration_api_key"
        )

        if st.button("💾 Save API Key", key="save_api_key", use_container_width=True, type="primary"):
            if api_key_input:
                # Basic validation
                if api_key_input.startswith('sk-ant-'):
                    st.session_state.ai_config['provider'] = 'claude'
                    st.session_state.ai_config['api_key'] = api_key_input
                    st.session_state.anthropic_key = api_key_input  # Legacy support
                    st.success("✅ API key saved!")
                    st.rerun()
                else:
                    st.error("This doesn't look like a Claude API key. It should start with `sk-ant-`")
            else:
                st.warning("Please enter an API key")

        st.caption("🔒 Your API key is stored in your browser session only. Never saved to any database.")
    else:
        st.markdown(f"""
        <div style="background: #f0fdfa; border-radius: 8px; padding: 0.75rem 1rem; margin-top: -0.5rem; margin-bottom: 1rem; border: 1px solid #a7f3d0;">
            <span style="color: #065f46;">✅ <strong>API key configured</strong> — Using {current_provider.title()}</span>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🗑️ Clear API Key", key="clear_api_key_integration"):
            st.session_state.ai_config['api_key'] = ''
            st.session_state.anthropic_key = ''
            st.rerun()

    # ===========================================
    # STEP 3: WordPress
    # ===========================================
    step3_complete = status['wordpress']
    step3_status_icon = "✅" if step3_complete else "3️⃣"
    step3_border_color = "#6ee7b7" if step3_complete else ("#fcd34d" if status['ai_key'] else "#e2e8f0")
    step3_bg = "linear-gradient(135deg, #f0fdfa 0%, #d1fae5 100%)" if step3_complete else ("linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)" if status['ai_key'] else "linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)")
    step3_header_color = "#065f46" if step3_complete else ("#92400e" if status['ai_key'] else "#64748b")
    step3_opacity = "1" if status['ai_key'] or step3_complete else "0.7"
    step3_complete_badge = '<span style="background: #d1fae5; color: #065f46; padding: 0.15rem 0.5rem; border-radius: 12px; font-size: 0.75rem; margin-left: 0.5rem;">✓ Complete</span>' if step3_complete else ''

    st.markdown(f"""
    <div style="background: {step3_bg}; border: 2px solid {step3_border_color}; border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem; opacity: {step3_opacity};">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span style="font-size: 1.5rem;">{step3_status_icon}</span>
            <div>
                <div style="font-size: 1.1rem; font-weight: 600; color: {step3_header_color};">
                    Step 3: Connect WordPress {step3_complete_badge}
                </div>
                <div style="font-size: 0.85rem; color: #64748b; margin-top: 0.25rem;">Apply fixes directly to your site</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not step3_complete:
        st.markdown("""
        <div style="background: #f8fafc; border-radius: 8px; padding: 1rem; margin-top: -0.5rem; margin-bottom: 1rem; border: 1px solid #e2e8f0;">
            <div style="font-size: 0.9rem; color: #475569; line-height: 1.6;">
                <strong>Why this matters:</strong> This is where the magic happens! Instead of logging into each post
                and clicking publish, we'll apply all your approved fixes automatically via the WordPress REST API.
                Fix hundreds of links in minutes, not hours.<br><br>
                <strong>How to get it:</strong> Generate an Application Password in your WordPress admin.
                Takes about 2 minutes. Your regular login password won't work — you need this special API password.
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📋 Step-by-step instructions", expanded=False):
            st.markdown("""
            1. Log into your **WordPress Admin** dashboard
            2. Go to **Users → Profile** (or click your name in the top-right)
            3. Scroll down to the **Application Passwords** section
            4. Enter name: `Screaming Fixes`
            5. Click **Add New Application Password**
            6. **Copy the password immediately** — you'll only see it once!
            7. Enter your details below

            **Note:** You need WordPress 5.6+ or the Application Passwords plugin.
            """)

        col1, col2 = st.columns(2)
        with col1:
            wp_url = st.text_input(
                "Site URL",
                placeholder="https://your-site.com",
                key="integration_wp_url"
            )
        with col2:
            wp_username = st.text_input(
                "Username",
                placeholder="admin",
                key="integration_wp_username"
            )

        wp_password = st.text_input(
            "Application Password (NOT your login password)",
            type="password",
            placeholder="xxxx xxxx xxxx xxxx xxxx xxxx",
            key="integration_wp_password"
        )

        if st.button("🔌 Connect to WordPress", key="connect_wp_integration", type="primary", use_container_width=True):
            if not all([wp_url, wp_username, wp_password]):
                st.error("Please fill in all fields")
            elif not WP_AVAILABLE:
                st.error("WordPress client not available. Check that wordpress_client.py is present.")
            else:
                with st.spinner("Connecting..."):
                    try:
                        client = WordPressClient(wp_url, wp_username, wp_password)
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

        st.caption("🔒 Credentials stored in your browser session only. Cleared when you close the tab.")
    else:
        st.markdown("""
        <div style="background: #f0fdfa; border-radius: 8px; padding: 0.75rem 1rem; margin-top: -0.5rem; margin-bottom: 0.5rem; border: 1px solid #a7f3d0;">
            <span style="color: #065f46;">✅ <strong>WordPress connected</strong> — Ready to apply fixes</span>
        </div>
        """, unsafe_allow_html=True)

        # Show detected SEO plugins
        render_detected_plugins()

        if st.button("🔌 Disconnect WordPress", key="disconnect_wp_integration"):
            if st.session_state.wp_client:
                st.session_state.wp_client.close()
            st.session_state.wp_connected = False
            st.session_state.wp_client = None
            # Clear SEO detection cache
            if 'seo_detection_summary' in st.session_state:
                del st.session_state.seo_detection_summary
            if 'seo_service' in st.session_state:
                del st.session_state.seo_service
            st.rerun()

    # ===========================================
    # COMPLETION MESSAGE
    # ===========================================
    if status['all_connected']:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); border: 2px solid #6ee7b7; border-radius: 12px; padding: 1.5rem; text-align: center; margin-top: 1rem;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎉</div>
            <div style="font-size: 1.25rem; font-weight: 600; color: #065f46; margin-bottom: 0.5rem;">
                All integrations complete!
            </div>
            <div style="font-size: 0.95rem; color: #047857;">
                You now have full access to all features. Upload a Screaming Frog report above to start fixing.
            </div>
        </div>
        """, unsafe_allow_html=True)
