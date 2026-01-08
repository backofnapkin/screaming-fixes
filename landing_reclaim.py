"""
Screaming Fixes - Backlink Reclaim Landing Page

A conversion-focused landing page that:
1. User enters a domain
2. Scans for broken backlinks (mock data for now)
3. Shows teaser results (top 3)
4. Captures email to unlock full results
5. Shows full results after email capture
"""

import re
import streamlit as st
from urllib.parse import urlparse


def clear_query_params():
    """Clear query params with fallback for older Streamlit versions"""
    try:
        st.query_params.clear()
    except AttributeError:
        st.experimental_set_query_params()


from config import (
    PRIMARY_TEAL,
    RECLAIM_TEASER_COUNT,
    RECLAIM_SESSION_LIMIT,
    RECLAIM_IP_DAILY_LIMIT
)
from services.supabase_client import SupabaseClient
from services.dataforseo_api import DataForSEOClient
from features.backlink_reclaim import load_scan_results, init_backlink_reclaim_state


def get_landing_css() -> str:
    """Get CSS for the landing page - matches main app teal branding"""
    return """
    <style>
        /* Import clean font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* Hide Streamlit chrome for landing page */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display: none;}

        /* Global font */
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* Center content container */
        .block-container {
            max-width: 700px !important;
            padding-top: 1.2rem !important;
            padding-bottom: 2rem !important;
        }

        /* Logo/Brand header */
        .brand-header {
            text-align: center;
            padding: 0.5rem 0 1rem 0;
            border-bottom: 1px solid #e2e8f0;
            margin-bottom: 1rem;
        }

        .brand-logo {
            font-size: 1.75rem;
            font-weight: 700;
            background: linear-gradient(135deg, #0d9488 0%, #0891b2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.02em;
        }

        /* Hero section */
        .hero-section {
            text-align: center;
            padding: 1rem 0;
        }

        .hero-title {
            font-size: 3.15rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 1rem;
            line-height: 1.2;
        }

        .hero-subtitle {
            font-size: 1.45rem;
            color: #64748b;
            margin-bottom: 1rem;
            line-height: 1.6;
        }

        .hero-subtitle strong {
            color: #0d9488;
        }

        /* Input fields */
        .stTextInput > div > div > input {
            border-radius: 8px !important;
            border: 2px solid #ccfbf1 !important;
            padding: 0.875rem 1rem !important;
            font-size: 1.1rem !important;
            transition: all 0.2s ease !important;
        }

        .stTextInput > div > div > input:focus {
            border-color: #14b8a6 !important;
            box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.15) !important;
        }

        .stTextInput > div > div > input::placeholder {
            color: #94a3b8 !important;
        }

        /* Button styling */
        .stButton > button {
            width: 100%;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 1.1rem !important;
            padding: 0.875rem 1.5rem !important;
            transition: all 0.2s ease !important;
        }

        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%) !important;
            border: none !important;
            color: white !important;
        }

        .stButton > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%) !important;
            box-shadow: 0 4px 12px rgba(20, 184, 166, 0.35) !important;
            transform: translateY(-1px);
        }

        /* Shimmer animation for scan button */
        @keyframes shimmer {
            0% { background-position: -200% center; }
            100% { background-position: 200% center; }
        }

        .shimmer-btn .stButton > button[kind="primary"] {
            background: linear-gradient(
                90deg,
                #14b8a6 0%,
                #14b8a6 40%,
                #5eead4 50%,
                #14b8a6 60%,
                #14b8a6 100%
            ) !important;
            background-size: 200% auto !important;
            animation: shimmer 3s ease-in-out infinite !important;
        }

        .shimmer-btn .stButton > button[kind="primary"]:hover {
            animation: none !important;
            background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%) !important;
            background-size: 100% auto !important;
        }

        /* Download button styling to match primary buttons */
        .stDownloadButton > button {
            width: 100%;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 1.1rem !important;
            padding: 0.875rem 1.5rem !important;
            transition: all 0.2s ease !important;
            background: #ffffff !important;
            border: 2px solid #14b8a6 !important;
            color: #0d9488 !important;
            height: 52px !important;
        }

        .stDownloadButton > button:hover {
            background: #f0fdfa !important;
            border-color: #0d9488 !important;
        }

        /* Make primary buttons same height */
        .stButton > button[kind="primary"] {
            height: 52px !important;
        }

        /* Results section */
        .results-header {
            font-size: 1.5rem;
            font-weight: 600;
            color: #0f172a;
            margin: 2rem 0 1rem 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* Metric cards */
        .metric-row {
            display: flex;
            gap: 1rem;
            margin: 1.5rem 0;
        }

        .metric-card {
            flex: 1;
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
        }

        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #0d9488;
        }

        .metric-label {
            font-size: 0.875rem;
            color: #64748b;
            margin-top: 0.25rem;
        }

        /* Backlink result cards */
        .backlink-card {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1rem;
            transition: all 0.2s ease;
        }

        .backlink-card:hover {
            border-color: #14b8a6;
            box-shadow: 0 4px 12px rgba(20, 184, 166, 0.1);
        }

        .backlink-referrer {
            font-weight: 600;
            color: #0f172a;
            font-size: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .backlink-rank {
            background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%);
            color: white;
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
        }

        .backlink-url {
            font-size: 0.875rem;
            color: #64748b;
            margin-top: 0.5rem;
            word-break: break-all;
        }

        .backlink-target {
            font-size: 0.8rem;
            color: #dc2626;
            margin-top: 0.25rem;
        }

        .backlink-meta {
            display: flex;
            gap: 1rem;
            margin-top: 0.5rem;
            font-size: 0.8rem;
            color: #94a3b8;
        }

        /* Teaser blur overlay */
        .teaser-overlay {
            position: relative;
            margin-top: 1rem;
        }

        .teaser-blur {
            filter: blur(4px);
            opacity: 0.5;
            pointer-events: none;
        }

        .teaser-cta {
            background: linear-gradient(135deg, #f0fdfa 0%, #ffffff 100%);
            border: 2px solid #14b8a6;
            border-radius: 16px;
            padding: 1rem;
            text-align: center;
            margin-top: 0.375rem;
        }

        .teaser-cta-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #0f172a;
            margin-bottom: 0.5rem;
        }

        .teaser-cta-subtitle {
            color: #64748b;
            margin-bottom: 1.5rem;
        }

        /* Email input special styling */
        .email-section .stTextInput > div > div > input {
            border-color: #14b8a6 !important;
        }

        /* Success message */
        .success-message {
            background: linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 100%);
            border: 1px solid #14b8a6;
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            margin: 1rem 0;
        }

        .success-message h3 {
            color: #0d9488;
            margin-bottom: 0.5rem;
        }

        /* Loading spinner */
        .scanning-indicator {
            text-align: center;
            padding: 3rem;
        }

        .scanning-text {
            color: #0d9488;
            font-weight: 500;
            margin-top: 1rem;
        }

        /* Footer */
        .landing-footer {
            text-align: center;
            padding: 2rem 0;
            color: #94a3b8;
            font-size: 0.875rem;
            border-top: 1px solid #e2e8f0;
            margin-top: 3rem;
        }

        /* Responsive */
        @media (max-width: 640px) {
            .hero-title {
                font-size: 1.875rem;
            }

            .hero-subtitle {
                font-size: 1.1rem;
            }

            .metric-row {
                flex-direction: column;
            }

            .scan-section {
                padding: 1.5rem;
            }
        }
    </style>
    """


def clean_domain(domain: str) -> str:
    """Clean and normalize domain input"""
    domain = domain.strip().lower()

    # Remove protocol
    if "://" in domain:
        parsed = urlparse(domain)
        domain = parsed.netloc or parsed.path

    # Remove www
    domain = domain.replace("www.", "")

    # Remove trailing slash
    domain = domain.rstrip("/")

    return domain


def is_valid_email(email: str) -> bool:
    """Basic email format validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def get_client_ip() -> str:
    """Get client IP address (returns empty string if unavailable)"""
    # Streamlit doesn't expose client IP directly
    # This would need to be configured at the deployment level
    return ""


def get_utm_params() -> dict:
    """Extract UTM parameters from query string"""
    try:
        params = st.query_params
        return {
            "utm_source": params.get("utm_source", ""),
            "utm_medium": params.get("utm_medium", ""),
            "utm_campaign": params.get("utm_campaign", "")
        }
    except AttributeError:
        # Fallback for older Streamlit versions
        params = st.experimental_get_query_params()
        return {
            "utm_source": params.get("utm_source", [""])[0],
            "utm_medium": params.get("utm_medium", [""])[0],
            "utm_campaign": params.get("utm_campaign", [""])[0]
        }


def render_backlink_card(backlink: dict, show_full: bool = True) -> str:
    """Render a single backlink result card"""
    dofollow_badge = "dofollow" if backlink.get("is_dofollow") else "nofollow"

    target_display = backlink.get("target_url", "")
    if len(target_display) > 60:
        target_display = target_display[:60] + "..."

    referring_display = backlink.get("referring_url", "")
    if len(referring_display) > 70:
        referring_display = referring_display[:70] + "..."

    return f"""
    <div class="backlink-card">
        <div class="backlink-referrer">
            <span>{backlink.get('referring_domain', '')}</span>
            <span class="backlink-rank">DR {backlink.get('domain_rank', 0)}</span>
        </div>
        <div class="backlink-url">{referring_display}</div>
        <div class="backlink-target">Dead link: {target_display}</div>
        <div class="backlink-meta">
            <span>{dofollow_badge}</span>
            <span>First seen: {backlink.get('first_seen', 'Unknown')}</span>
        </div>
    </div>
    """


def group_backlinks_by_dead_page(backlinks: list) -> list:
    """Group backlinks by dead page (target URL) and return sorted opportunities"""
    dead_pages = {}
    for bl in backlinks:
        target = bl.get("target_url", "")
        if not target:
            continue
        if target not in dead_pages:
            dead_pages[target] = {
                "dead_page": target,
                "backlinks_count": 0,
                "referrers_by_domain": {}  # domain -> {rank, link_count}
            }
        dead_pages[target]["backlinks_count"] += 1

        # Aggregate by referring domain
        domain = bl.get("referring_domain", "")
        rank = bl.get("domain_rank", 0)
        if domain:
            if domain not in dead_pages[target]["referrers_by_domain"]:
                dead_pages[target]["referrers_by_domain"][domain] = {
                    "rank": rank,
                    "link_count": 0
                }
            dead_pages[target]["referrers_by_domain"][domain]["link_count"] += 1
            # Update rank if higher (in case of multiple links from same domain)
            if rank > dead_pages[target]["referrers_by_domain"][domain]["rank"]:
                dead_pages[target]["referrers_by_domain"][domain]["rank"] = rank

    # Process each dead page to create sorted referrer list
    for page_data in dead_pages.values():
        referrers_list = [
            {"domain": domain, "rank": info["rank"], "link_count": info["link_count"]}
            for domain, info in page_data["referrers_by_domain"].items()
        ]
        # Sort by DR (rank) descending
        referrers_list.sort(key=lambda x: x["rank"], reverse=True)
        page_data["referrers"] = referrers_list
        page_data["unique_domains"] = len(referrers_list)
        # Calculate max DR for sorting opportunities
        page_data["max_dr"] = referrers_list[0]["rank"] if referrers_list else 0

    # Sort by max DR (highest value domains first), then by backlink count
    opportunities = sorted(dead_pages.values(), key=lambda x: (x["max_dr"], x["backlinks_count"]), reverse=True)
    return opportunities


def render_opportunity_card(opportunity: dict) -> str:
    """Render a single opportunity card emphasizing referring domains"""
    dead_page = opportunity.get("dead_page", "")
    backlinks_count = opportunity.get("backlinks_count", 0)
    referrers = opportunity.get("referrers", [])
    unique_domains = opportunity.get("unique_domains", 0)

    # Extract just the path from the dead page URL for cleaner display
    try:
        from urllib.parse import urlparse
        parsed = urlparse(dead_page)
        dead_page_path = parsed.path or "/"
        if len(dead_page_path) > 45:
            dead_page_path = dead_page_path[:45] + "..."
    except Exception:
        dead_page_path = dead_page[:50] + "..." if len(dead_page) > 50 else dead_page

    # Build the referrer list HTML (show top 3 domains)
    referrer_items = []
    for ref in referrers[:3]:
        domain = ref.get("domain", "")
        rank = ref.get("rank", 0)
        link_count = ref.get("link_count", 1)
        link_text = f"{link_count} link{'s' if link_count != 1 else ''}"
        referrer_items.append(
            f'<div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.35rem 0;">'
            f'<span style="color: #475569; margin-right: 0.25rem;">•</span>'
            f'<span style="font-weight: 600; color: #0f172a;">{domain}</span>'
            f'<span style="background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%); color: white; font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.4rem; border-radius: 4px; margin-left: 0.25rem;">DR {rank}</span>'
            f'<span style="color: #64748b; font-size: 0.85rem; margin-left: 0.25rem;">— {link_text}</span>'
            f'</div>'
        )

    referrers_html = "".join(referrer_items)

    # Show "+X more" if there are additional domains
    more_html = ""
    if unique_domains > 3:
        more_count = unique_domains - 3
        more_html = f'<div style="color: #64748b; font-size: 0.85rem; padding-left: 1rem; margin-top: 0.25rem;">+ {more_count} more site{"s" if more_count != 1 else ""}</div>'

    # Build complete card HTML as single string
    card_html = f'''<div class="backlink-card">
<div style="font-size: 0.95rem; color: #dc2626; font-weight: 600; margin-bottom: 0.75rem;">🔗 {dead_page_path} <span style="font-weight: 400; color: #94a3b8;">is broken</span></div>
<div style="font-size: 0.85rem; color: #64748b; margin-bottom: 0.5rem;">You're losing links from:</div>
<div style="margin-left: 0.25rem;">{referrers_html}{more_html}</div>
<div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #f1f5f9;"><span style="background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); color: white; padding: 0.25rem 0.6rem; border-radius: 4px; font-size: 0.8rem; font-weight: 600;">{backlinks_count} backlink{'s' if backlinks_count != 1 else ''} at risk</span></div>
</div>'''

    return card_html


def generate_csv_export(backlinks: list, domain: str) -> str:
    """Generate CSV export of broken backlinks"""
    import io
    import csv

    # Group backlinks by target URL (dead page)
    dead_pages = {}
    for bl in backlinks:
        target = bl.get("target_url", "")
        if target not in dead_pages:
            dead_pages[target] = {
                "dead_page": target,
                "backlinks_count": 0,
                "top_referrer": "",
                "top_referrer_rank": 0,
                "all_referrers": []
            }
        dead_pages[target]["backlinks_count"] += 1
        dead_pages[target]["all_referrers"].append(bl.get("referring_domain", ""))

        # Track top referrer by domain rank
        if bl.get("domain_rank", 0) > dead_pages[target]["top_referrer_rank"]:
            dead_pages[target]["top_referrer"] = bl.get("referring_domain", "")
            dead_pages[target]["top_referrer_rank"] = bl.get("domain_rank", 0)

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Dead Page", "Backlinks Count", "Top Referrer", "All Referrers"])

    for page_data in dead_pages.values():
        writer.writerow([
            page_data["dead_page"],
            page_data["backlinks_count"],
            page_data["top_referrer"],
            "; ".join(page_data["all_referrers"])
        ])

    return output.getvalue()


def render_landing_page():
    """Main landing page renderer"""

    # Apply custom CSS
    st.markdown(get_landing_css(), unsafe_allow_html=True)

    # Initialize services
    supabase = SupabaseClient()
    dataforseo = DataForSEOClient()

    # Session state initialization
    if "scan_results" not in st.session_state:
        st.session_state.scan_results = None
    if "email_captured" not in st.session_state:
        st.session_state.email_captured = False
    if "scanned_domain" not in st.session_state:
        st.session_state.scanned_domain = ""
    if "session_scan_count" not in st.session_state:
        st.session_state.session_scan_count = 0

    # Brand header
    st.markdown("""
        <div class="brand-header">
            <div class="brand-logo">🔧 Screaming Fixes</div>
        </div>
    """, unsafe_allow_html=True)

    # Hero section
    st.markdown("""
        <div class="hero-section">
            <h1 class="hero-title">Find Your Dead Backlinks and Fix Them in 5 Minutes</h1>
            <p class="hero-subtitle">
                Discover <strong>broken backlinks</strong> pointing to your site, then reclaim them with Screaming Fixes.
                Turn 404 errors into rankings and LLM visibility. <strong>This tool is FREE.</strong>
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Domain input with label
    st.markdown("""
        <p style="text-align: center; color: #64748b; margin-bottom: 0.5rem; font-size: 1rem;">
            Enter your website URL
        </p>
    """, unsafe_allow_html=True)

    domain_input = st.text_input(
        "Enter your website URL",
        placeholder="example.com",
        label_visibility="collapsed",
        key="domain_input"
    )

    # Check rate limits before showing scan button
    ip_address = get_client_ip()
    ip_scan_count = supabase.get_ip_scan_count_today(ip_address) if ip_address else 0
    session_scan_count = st.session_state.session_scan_count

    # Determine if user is rate limited
    session_limit_reached = session_scan_count >= RECLAIM_SESSION_LIMIT
    ip_limit_reached = ip_scan_count >= RECLAIM_IP_DAILY_LIMIT
    is_rate_limited = session_limit_reached or ip_limit_reached

    # Show remaining scans info if they've used any
    if session_scan_count > 0 and not is_rate_limited:
        remaining_session = RECLAIM_SESSION_LIMIT - session_scan_count
        remaining_ip = RECLAIM_IP_DAILY_LIMIT - ip_scan_count
        remaining = min(remaining_session, remaining_ip)
        st.markdown(f"""
            <p style="text-align: center; color: #64748b; font-size: 0.85rem; margin-top: 0.5rem;">
                {remaining} free scan{'s' if remaining != 1 else ''} remaining
            </p>
        """, unsafe_allow_html=True)

    # Show rate limit message if exceeded
    if is_rate_limited:
        st.markdown("""
            <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border: 2px solid #f59e0b; border-radius: 12px; padding: 1.5rem; text-align: center; margin: 1rem 0;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">⏰</div>
                <h3 style="color: #92400e; margin-bottom: 0.5rem; font-size: 1.25rem;">Daily Scan Limit Reached</h3>
                <p style="color: #a16207; font-size: 1rem; line-height: 1.5;">
                    You've used all your free scans for today. Come back tomorrow for more, or explore our main tool below to fix other SEO issues on your site.
                </p>
            </div>
        """, unsafe_allow_html=True)

        if st.button("🔧 Explore Screaming Fixes", type="primary", use_container_width=True, key="rate_limit_cta"):
            clear_query_params()
            st.rerun()

    # Wrap scan button with shimmer effect
    st.markdown('<div class="shimmer-btn">', unsafe_allow_html=True)
    scan_clicked = st.button(
        "Scan for Broken Backlinks",
        type="primary",
        use_container_width=True,
        disabled=is_rate_limited
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Handle scan
    if scan_clicked and domain_input and not is_rate_limited:
        domain = clean_domain(domain_input)

        if not domain or "." not in domain:
            st.error("Please enter a valid domain (e.g., example.com)")
        else:
            with st.spinner("Scanning backlinks..."):
                # Get backlink data (tries real API first, falls back to mock)
                backlinks, broken_count, total_count, api_cost, error = dataforseo.get_broken_backlinks(domain)

                if error:
                    st.error(f"Scan failed: {error}")
                else:
                    top_referrers = dataforseo.get_top_referrers(backlinks, limit=5)

                    # Store in session state
                    st.session_state.scan_results = {
                        "domain": domain,
                        "backlinks": backlinks,
                        "broken_count": broken_count,
                        "total_count": total_count,
                        "top_referrers": top_referrers,
                        "api_cost": api_cost
                    }
                    st.session_state.scanned_domain = domain
                    st.session_state.email_captured = False

                    # Increment session scan counter for rate limiting
                    st.session_state.session_scan_count += 1

                    # Save scan to database (also used for IP rate limiting)
                    supabase.create_scan(
                        domain=domain,
                        broken_backlinks_count=broken_count,
                        total_backlinks=total_count,
                        results_json=backlinks,
                        ip_address=ip_address,
                        api_cost_cents=api_cost
                    )

                    st.rerun()

    # Display results
    if st.session_state.scan_results:
        results = st.session_state.scan_results
        backlinks = results["backlinks"]

        # Results header
        st.markdown(f"""
            <div class="results-header">
                Results for {results['domain']}
            </div>
        """, unsafe_allow_html=True)

        # Check for zero broken backlinks - show congratulations
        if results['broken_count'] == 0:
            st.markdown("""
                <div style="background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border: 2px solid #10b981; border-radius: 16px; padding: 2rem; text-align: center; margin: 1rem 0 2rem 0;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🏆</div>
                    <h2 style="color: #065f46; margin-bottom: 0.75rem; font-size: 1.75rem;">Your Backlink Game is STRONG!</h2>
                    <p style="color: #047857; font-size: 1.1rem; margin-bottom: 0.5rem; font-weight: 600;">
                        Zero broken backlinks found. You're either an SEO wizard or you've been secretly using Screaming Fixes already.
                    </p>
                    <p style="color: #059669; font-size: 1rem; line-height: 1.6;">
                        Your link equity is intact and Google is happy. But don't get too comfortable... there's always more SEO to fix!
                    </p>
                </div>
            """, unsafe_allow_html=True)

            # CTA to main tool
            st.markdown("""
                <div style="background: linear-gradient(135deg, #f0fdfa 0%, #ffffff 100%); border: 2px solid #14b8a6; border-radius: 16px; padding: 1.5rem; text-align: center;">
                    <h3 style="color: #0f172a; margin-bottom: 0.75rem; font-size: 1.25rem;">While you're here...</h3>
                    <p style="color: #64748b; margin-bottom: 1rem; line-height: 1.6;">
                        Screaming Fixes can help with other SEO gremlins lurking on your site: <strong>404 errors</strong>, <strong>redirect loops</strong>, <strong>broken internal links</strong>, <strong>schema markup issues</strong>, and more. All fixable with one click to WordPress.
                    </p>
                </div>
            """, unsafe_allow_html=True)

            if st.button("🔧 Explore Screaming Fixes", type="primary", use_container_width=True):
                clear_query_params()
                st.rerun()

            st.markdown("""
                <p style="text-align: center; color: #64748b; font-size: 0.9rem; margin-top: 1rem;">
                    Or scan another domain above to check for broken backlinks
                </p>
            """, unsafe_allow_html=True)

        else:
            # Metrics (only show when there are broken backlinks)
            st.markdown(f"""
                <div class="metric-row">
                    <div class="metric-card">
                        <div class="metric-value">{results['broken_count']}</div>
                        <div class="metric-label">Broken Backlinks</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{results['total_count']}</div>
                        <div class="metric-label">Total Backlinks</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Show teaser or full results
            if not st.session_state.email_captured:
                # Group backlinks by dead page to show opportunities
                opportunities = group_backlinks_by_dead_page(backlinks)
                total_opportunities = len(opportunities)

                # Show top 3 opportunities (dead pages with most backlinks)
                st.markdown("### Top Opportunities", unsafe_allow_html=True)

                teaser_opportunities = opportunities[:3]
                for opp in teaser_opportunities:
                    st.markdown(render_opportunity_card(opp), unsafe_allow_html=True)

                # Email capture CTA
                st.markdown(f"""
                    <div class="teaser-cta">
                        <div class="teaser-cta-title">Unlock All {total_opportunities} Dead Pages ({results['broken_count']} Backlinks)</div>
                    </div>
                """, unsafe_allow_html=True)

                # Email input with label
                st.markdown('<div class="email-section">', unsafe_allow_html=True)
                st.markdown("""
                    <p style="text-align: center; color: #64748b; margin-bottom: 0.5rem; font-size: 1rem;">
                        Enter your email address
                    </p>
                """, unsafe_allow_html=True)
                email_input = st.text_input(
                    "Enter your email address",
                    placeholder="you@example.com",
                    label_visibility="collapsed",
                    key="email_input"
                )

                # Description text below
                st.markdown("""
                    <p style="text-align: center; color: #64748b; font-size: 0.9rem; margin-top: 0.5rem; line-height: 1.5;">
                        Enter your email to see the full list and fix all of these links now. This tool is 100% free and unlocks other features like broken links, redirect chains, and technical SEO fixes you can push directly to WordPress.
                    </p>
                """, unsafe_allow_html=True)

                unlock_clicked = st.button("Unlock Full Results", type="primary", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

                if unlock_clicked:
                    if not email_input:
                        st.error("Please enter your email address")
                    elif not is_valid_email(email_input):
                        st.error("Please enter a valid email address")
                    else:
                        # Save lead
                        utm = get_utm_params()
                        ip_address = get_client_ip()

                        lead = supabase.create_lead(
                            email=email_input,
                            domain=results["domain"],
                            broken_backlinks_count=results["broken_count"],
                            top_referrers=results["top_referrers"],
                            ip_address=ip_address,
                            utm_source=utm["utm_source"],
                            utm_medium=utm["utm_medium"],
                            utm_campaign=utm["utm_campaign"]
                        )

                        st.session_state.email_captured = True
                        st.rerun()

            else:
                # =========================================================
                # POST-EMAIL CAPTURE: Full Results View
                # =========================================================

                # Calculate summary stats for the CTA
                opportunities = group_backlinks_by_dead_page(backlinks)
                unique_domains = set()
                for bl in backlinks:
                    if bl.get("referring_domain"):
                        unique_domains.add(bl.get("referring_domain"))
                unique_domain_count = len(unique_domains)

                # Get top 3 referring domains by DR
                domain_dr_map = {}
                for bl in backlinks:
                    domain = bl.get("referring_domain", "")
                    dr = bl.get("domain_rank", 0)
                    if domain and (domain not in domain_dr_map or dr > domain_dr_map[domain]):
                        domain_dr_map[domain] = dr
                top_domains = sorted(domain_dr_map.items(), key=lambda x: x[1], reverse=True)[:3]
                top_domains_text = ", ".join([f"{d[0]} (DR {d[1]})" for d in top_domains])

                # Determine urgency level based on DR scores
                max_dr = top_domains[0][1] if top_domains else 0
                if max_dr >= 70:
                    urgency = "CRITICAL"
                    urgency_color = "#dc2626"
                elif max_dr >= 50:
                    urgency = "HIGH"
                    urgency_color = "#ea580c"
                elif max_dr >= 30:
                    urgency = "MEDIUM"
                    urgency_color = "#ca8a04"
                else:
                    urgency = "LOW"
                    urgency_color = "#65a30d"

                # =========================================================
                # 1. PRIMARY CTA BOX - Above the fold
                # =========================================================
                st.markdown(f'''
<div style="background: linear-gradient(135deg, #0d9488 0%, #0891b2 100%); border-radius: 16px; padding: 2rem; text-align: center; margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(13, 148, 136, 0.3);">
<h2 style="color: white; margin: 0 0 1rem 0; font-size: 1.75rem;">🎯 Ready to reclaim these backlinks?</h2>
<p style="color: rgba(255,255,255,0.9); font-size: 1.1rem; margin-bottom: 1.5rem; line-height: 1.6;">You have <strong style="color: white;">{results["broken_count"]} broken backlinks</strong> from {unique_domain_count} domains including {top_domains_text}. Fix them in 5 minutes.</p>
<div style="display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; margin-top: 1rem;">
<span style="color: rgba(255,255,255,0.85); font-size: 0.9rem;">✓ Connect WordPress</span>
<span style="color: rgba(255,255,255,0.85); font-size: 0.9rem;">✓ AI suggests redirects</span>
<span style="color: rgba(255,255,255,0.85); font-size: 0.9rem;">✓ One-click fix</span>
</div>
</div>
                ''', unsafe_allow_html=True)

                # Big primary CTA button
                if st.button("🚀 Fix These Now — It's Free", type="primary", use_container_width=True, key="top_cta"):
                    # Initialize backlink reclaim state
                    init_backlink_reclaim_state()

                    # Build scan results object for the fix workflow
                    fix_scan_results = {
                        'domain': results['domain'],
                        'broken_backlinks': backlinks,
                        'broken_count': results['broken_count'],
                        'total_count': results['total_count'],
                        'api_cost_cents': results.get('api_cost', 0),
                    }

                    # Load into br_ session state using the shared function
                    load_scan_results(fix_scan_results, results['domain'])

                    # Set current task to backlink_reclaim
                    st.session_state.current_task = 'backlink_reclaim'
                    st.session_state.task_type = 'backlink_reclaim'

                    # Set flag to navigate to main tool on next rerun
                    st.session_state.navigate_to_fix_workflow = True
                    st.session_state.br_scroll_to_section = True
                    st.session_state.br_from_landing = True

                    clear_query_params()
                    st.rerun()

                # =========================================================
                # 2. VALUE SUMMARY - What they're losing
                # =========================================================
                st.markdown(f'''
<div style="background: #fefce8; border: 1px solid #fef08a; border-radius: 12px; padding: 1.25rem; margin: 1.5rem 0;">
<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
<div>
<span style="font-weight: 600; color: #854d0e; font-size: 1rem;">⚠️ Link equity at risk:</span>
<span style="background: {urgency_color}; color: white; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.85rem; font-weight: 700; margin-left: 0.5rem;">{urgency}</span>
</div>
<div style="color: #854d0e; font-size: 0.9rem;">
<strong>{results["broken_count"]}</strong> backlinks from <strong>{unique_domain_count}</strong> domains
</div>
</div>
<div style="margin-top: 0.75rem; color: #a16207; font-size: 0.9rem;">
<strong>Top referring domains:</strong> {top_domains_text}
</div>
</div>
                ''', unsafe_allow_html=True)

                # =========================================================
                # 3. RESULTS LIST - Scrollable details
                # =========================================================
                total_backlinks = len(backlinks)
                per_page = 10

                if "backlinks_page" not in st.session_state:
                    st.session_state.backlinks_page = 0

                total_pages = (total_backlinks + per_page - 1) // per_page
                current_page = st.session_state.backlinks_page

                if current_page >= total_pages:
                    current_page = max(0, total_pages - 1)
                    st.session_state.backlinks_page = current_page

                start_idx = current_page * per_page
                end_idx = min(start_idx + per_page, total_backlinks)

                st.markdown(f'''
<div style="display: flex; justify-content: space-between; align-items: center; margin: 1.5rem 0 1rem 0;">
<h3 style="margin: 0; color: #0f172a;">All Broken Backlinks</h3>
<span style="color: #64748b; font-size: 0.9rem;">{total_backlinks} total</span>
</div>
                ''', unsafe_allow_html=True)

                for bl in backlinks[start_idx:end_idx]:
                    st.markdown(render_backlink_card(bl), unsafe_allow_html=True)

                # Pagination controls
                if total_pages > 1:
                    st.markdown(f'''
<p style="text-align: center; color: #64748b; margin: 1rem 0 0.5rem 0;">
Showing {start_idx + 1}-{end_idx} of {total_backlinks} backlinks
</p>
                    ''', unsafe_allow_html=True)

                    col_prev, col_page, col_next = st.columns([1, 2, 1])

                    with col_prev:
                        if current_page > 0:
                            if st.button("← Previous", key="prev_page", use_container_width=True):
                                st.session_state.backlinks_page = current_page - 1
                                st.rerun()

                    with col_page:
                        st.markdown(f'''
<p style="text-align: center; color: #0d9488; font-weight: 600; padding: 0.5rem 0;">
Page {current_page + 1} of {total_pages}
</p>
                        ''', unsafe_allow_html=True)

                    with col_next:
                        if current_page < total_pages - 1:
                            if st.button("Next →", key="next_page", use_container_width=True):
                                st.session_state.backlinks_page = current_page + 1
                                st.rerun()

                # =========================================================
                # 4. BOTTOM CTA + Export Options
                # =========================================================
                st.markdown('''
<div style="background: linear-gradient(135deg, #f0fdfa 0%, #ecfeff 100%); border: 2px solid #14b8a6; border-radius: 16px; padding: 1.5rem; text-align: center; margin-top: 2rem;">
<h3 style="color: #0f172a; margin: 0 0 0.5rem 0; font-size: 1.25rem;">Don't let this link equity go to waste</h3>
<p style="color: #64748b; margin-bottom: 1rem; font-size: 0.95rem;">Screaming Fixes connects to WordPress and creates redirects automatically.</p>
</div>
                ''', unsafe_allow_html=True)

                if st.button("🚀 Fix These Now", type="primary", use_container_width=True, key="bottom_cta"):
                    init_backlink_reclaim_state()
                    fix_scan_results = {
                        'domain': results['domain'],
                        'broken_backlinks': backlinks,
                        'broken_count': results['broken_count'],
                        'total_count': results['total_count'],
                        'api_cost_cents': results.get('api_cost', 0),
                    }
                    load_scan_results(fix_scan_results, results['domain'])
                    st.session_state.current_task = 'backlink_reclaim'
                    st.session_state.task_type = 'backlink_reclaim'
                    st.session_state.navigate_to_fix_workflow = True
                    st.session_state.br_scroll_to_section = True
                    st.session_state.br_from_landing = True
                    clear_query_params()
                    st.rerun()

                # Export options (secondary)
                st.markdown('''
<p style="text-align: center; color: #64748b; margin: 1rem 0 0.5rem 0; font-size: 0.9rem;">Or export for later:</p>
                ''', unsafe_allow_html=True)

                csv_data = generate_csv_export(backlinks, results["domain"])
                col_csv, col_spacer = st.columns([1, 1])
                with col_csv:
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=f"{results['domain']}_broken_backlinks.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                # Social proof
                st.markdown('''
<p style="text-align: center; color: #94a3b8; margin-top: 1.5rem; font-size: 0.85rem;">
✨ Join 100+ SEOs who've reclaimed their backlinks with Screaming Fixes
</p>
                ''', unsafe_allow_html=True)

    # Footer with navigation
    st.markdown("""
        <div class="landing-footer">
            <p style="color: #0d9488; font-weight: 500; margin-bottom: 1rem;">The SEO fixer that actually pushes changes to WordPress</p>
            <div style="display: flex; justify-content: center; gap: 2rem; margin-bottom: 1rem; flex-wrap: wrap;">
                <a href="/" style="color: #64748b; text-decoration: none; font-weight: 500; transition: color 0.2s;">Home</a>
                <a href="/#about" style="color: #64748b; text-decoration: none; font-weight: 500; transition: color 0.2s;">About</a>
                <a href="/#instructions" style="color: #64748b; text-decoration: none; font-weight: 500; transition: color 0.2s;">Instructions</a>
                <a href="mailto:brett.lindenberg@gmail.com" style="color: #64748b; text-decoration: none; font-weight: 500; transition: color 0.2s;">Contact</a>
            </div>
            <p>🔧 Screaming Fixes - AI-Powered SEO Tools</p>
        </div>
    """, unsafe_allow_html=True)


# Allow running standalone for testing
if __name__ == "__main__":
    render_landing_page()
