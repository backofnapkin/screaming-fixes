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

from config import PRIMARY_TEAL, RECLAIM_TEASER_COUNT
from services.supabase_client import SupabaseClient
from services.dataforseo_api import DataForSEOClient


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
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }

        /* Logo/Brand header */
        .brand-header {
            text-align: center;
            padding: 1rem 0 2rem 0;
            border-bottom: 1px solid #e2e8f0;
            margin-bottom: 2rem;
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
            padding: 2rem 0;
        }

        .hero-title {
            font-size: 2.5rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 1rem;
            line-height: 1.2;
        }

        .hero-subtitle {
            font-size: 1.25rem;
            color: #64748b;
            margin-bottom: 2rem;
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
    params = st.query_params
    return {
        "utm_source": params.get("utm_source", ""),
        "utm_medium": params.get("utm_medium", ""),
        "utm_campaign": params.get("utm_campaign", "")
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

    # Brand header
    st.markdown("""
        <div class="brand-header">
            <div class="brand-logo">🔧 Screaming Fixes</div>
        </div>
    """, unsafe_allow_html=True)

    # Hero section
    st.markdown("""
        <div class="hero-section">
            <h1 class="hero-title">Find Your Lost Backlinks and Fix Them in 5 Minutes</h1>
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

    scan_clicked = st.button("Scan for Broken Backlinks", type="primary", use_container_width=True)

    # Handle scan
    if scan_clicked and domain_input:
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

                    # Save scan to database
                    ip_address = get_client_ip()
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

        # Metrics
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
            # Show top 3 results
            st.markdown("### Top Opportunities", unsafe_allow_html=True)

            teaser_backlinks = backlinks[:RECLAIM_TEASER_COUNT]
            for bl in teaser_backlinks:
                st.markdown(render_backlink_card(bl), unsafe_allow_html=True)

            # Blurred preview of remaining
            if len(backlinks) > RECLAIM_TEASER_COUNT:
                remaining_count = len(backlinks) - RECLAIM_TEASER_COUNT

                st.markdown('<div class="teaser-overlay">', unsafe_allow_html=True)

                # Show 2 blurred cards
                st.markdown('<div class="teaser-blur">', unsafe_allow_html=True)
                for bl in backlinks[RECLAIM_TEASER_COUNT:RECLAIM_TEASER_COUNT + 2]:
                    st.markdown(render_backlink_card(bl), unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

            # Email capture CTA
            st.markdown(f"""
                <div class="teaser-cta">
                    <div class="teaser-cta-title">Unlock All {results['broken_count']} Broken Backlinks</div>
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
            # Full results view
            st.markdown("""
                <div class="success-message">
                    <h3>Results Unlocked!</h3>
                    <p>You're losing link equity from these dead pages. Export the list or fix them now.</p>
                </div>
                <style>
                    /* Equal button heights for action buttons */
                    .action-buttons-row .stButton > button,
                    .action-buttons-row .stDownloadButton > button {
                        height: 48px !important;
                        min-height: 48px !important;
                        padding: 0.5rem 1rem !important;
                    }
                </style>
            """, unsafe_allow_html=True)

            # Action buttons row
            st.markdown('<div class="action-buttons-row">', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 Fix These Now", type="primary", use_container_width=True):
                    st.query_params.clear()
                    st.rerun()
            with col2:
                # Generate CSV data
                csv_data = generate_csv_export(backlinks, results["domain"])
                st.download_button(
                    label="📥 Export CSV",
                    data=csv_data,
                    file_name=f"{results['domain']}_broken_backlinks.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            st.markdown('</div>', unsafe_allow_html=True)

            # Full results table with pagination
            total_backlinks = len(backlinks)
            per_page = 10

            # Initialize pagination state
            if "backlinks_page" not in st.session_state:
                st.session_state.backlinks_page = 0

            total_pages = (total_backlinks + per_page - 1) // per_page  # Ceiling division
            current_page = st.session_state.backlinks_page

            # Ensure current page is within bounds
            if current_page >= total_pages:
                current_page = max(0, total_pages - 1)
                st.session_state.backlinks_page = current_page

            start_idx = current_page * per_page
            end_idx = min(start_idx + per_page, total_backlinks)

            st.markdown(f"### All Broken Backlinks ({total_backlinks} total)", unsafe_allow_html=True)

            # Show current page of results
            for bl in backlinks[start_idx:end_idx]:
                st.markdown(render_backlink_card(bl), unsafe_allow_html=True)

            # Pagination controls
            if total_pages > 1:
                st.markdown(f"""
                    <p style="text-align: center; color: #64748b; margin: 1rem 0 0.5rem 0;">
                        Showing {start_idx + 1}-{end_idx} of {total_backlinks} backlinks
                    </p>
                """, unsafe_allow_html=True)

                col_prev, col_page, col_next = st.columns([1, 2, 1])

                with col_prev:
                    if current_page > 0:
                        if st.button("← Previous", key="prev_page", use_container_width=True):
                            st.session_state.backlinks_page = current_page - 1
                            st.rerun()

                with col_page:
                    st.markdown(f"""
                        <p style="text-align: center; color: #0d9488; font-weight: 600; padding: 0.5rem 0;">
                            Page {current_page + 1} of {total_pages}
                        </p>
                    """, unsafe_allow_html=True)

                with col_next:
                    if current_page < total_pages - 1:
                        if st.button("Next →", key="next_page", use_container_width=True):
                            st.session_state.backlinks_page = current_page + 1
                            st.rerun()

            # Bottom CTA section
            st.markdown("""
                <div style="background: linear-gradient(135deg, #f0fdfa 0%, #ecfeff 100%); border: 2px solid #14b8a6; border-radius: 16px; padding: 2rem; text-align: center; margin-top: 2rem;">
                    <h3 style="color: #0f172a; margin-bottom: 0.75rem; font-size: 1.5rem;">Ready to reclaim this link equity?</h3>
                    <p style="color: #64748b; margin-bottom: 1.5rem; line-height: 1.6;">
                        Screaming Fixes connects to your WordPress site and creates redirects for these dead pages in minutes. No manual .htaccess editing. No plugins to configure.
                    </p>
                </div>
            """, unsafe_allow_html=True)

            if st.button("🔧 Open Screaming Fixes", type="primary", use_container_width=True, key="bottom_cta"):
                st.query_params.clear()
                st.rerun()

            st.markdown("""
                <p style="text-align: center; color: #0d9488; font-weight: 500; margin-top: 1rem;">
                    The SEO fixer that actually pushes changes to WordPress
                </p>
            """, unsafe_allow_html=True)

    # Footer with navigation
    st.markdown("""
        <div class="landing-footer">
            <p style="color: #0d9488; font-weight: 500; margin-bottom: 1rem;">The SEO fixer that actually pushes changes to WordPress</p>
            <div style="display: flex; justify-content: center; gap: 2rem; margin-bottom: 1rem; flex-wrap: wrap;">
                <a href="/" style="color: #64748b; text-decoration: none; font-weight: 500; transition: color 0.2s;">Home</a>
                <a href="/#about" style="color: #64748b; text-decoration: none; font-weight: 500; transition: color 0.2s;">About</a>
                <a href="/#instructions" style="color: #64748b; text-decoration: none; font-weight: 500; transition: color 0.2s;">Instructions</a>
                <a href="mailto:contact@screamingfixes.com" style="color: #64748b; text-decoration: none; font-weight: 500; transition: color 0.2s;">Contact</a>
            </div>
            <p>🔧 Screaming Fixes - AI-Powered SEO Tools</p>
        </div>
    """, unsafe_allow_html=True)


# Allow running standalone for testing
if __name__ == "__main__":
    render_landing_page()
