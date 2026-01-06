"""
DataForSEO API client for backlink analysis
Falls back to realistic mock data when API credentials are not configured
"""

import random
import hashlib
import base64
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import requests

from config import (
    DATAFORSEO_LOGIN,
    DATAFORSEO_PASSWORD,
    USE_MOCK_DATA,
    RECLAIM_MIN_BROKEN,
    RECLAIM_MAX_BROKEN
)


# Realistic referrer domains for mock data
MOCK_REFERRER_DOMAINS = [
    "forbes.com",
    "reddit.com",
    "medium.com",
    "twitter.com",
    "linkedin.com",
    "quora.com",
    "techcrunch.com",
    "mashable.com",
    "huffpost.com",
    "businessinsider.com",
    "inc.com",
    "entrepreneur.com",
    "fastcompany.com",
    "wired.com",
    "theverge.com",
    "arstechnica.com",
    "zdnet.com",
    "cnet.com",
    "engadget.com",
    "gizmodo.com",
    "lifehacker.com",
    "producthunt.com",
    "hackernews.com",
    "dev.to",
    "stackoverflow.com",
    "github.com",
    "wikipedia.org",
    "nytimes.com",
    "theguardian.com",
    "bbc.com",
    "cnn.com",
    "bloomberg.com",
    "reuters.com",
    "wsj.com",
    "yahoo.com"
]

# Common dead page path patterns
MOCK_DEAD_PATHS = [
    "/blog/{slug}-guide",
    "/resources/{slug}",
    "/2019/{slug}",
    "/2020/{slug}",
    "/2021/{slug}",
    "/old-posts/{slug}",
    "/archived/{slug}",
    "/deleted-content/{slug}",
    "/legacy/{slug}",
    "/outdated/{slug}",
    "/removed/{slug}",
    "/blog/old/{slug}",
    "/posts/{slug}-tutorial",
    "/articles/{slug}",
    "/news/{slug}",
    "/guides/{slug}-complete-guide",
    "/resources/download-{slug}",
    "/tools/{slug}",
    "/products/discontinued-{slug}",
    "/case-studies/{slug}"
]

# Slug components for generating realistic URLs
SLUG_WORDS = [
    "ultimate", "complete", "best", "top", "guide", "tutorial",
    "howto", "review", "comparison", "tips", "strategies",
    "growth", "marketing", "seo", "content", "social", "email",
    "analytics", "tools", "software", "startup", "business",
    "productivity", "automation", "workflow", "integration"
]


def _generate_seed(domain: str) -> int:
    """Generate a consistent seed from domain for reproducible mock data"""
    return int(hashlib.md5(domain.encode()).hexdigest()[:8], 16)


def _generate_slug() -> str:
    """Generate a realistic URL slug"""
    words = random.sample(SLUG_WORDS, random.randint(2, 4))
    return "-".join(words)


def _generate_mock_backlink(target_domain: str) -> Dict:
    """Generate a single mock broken backlink"""
    referrer_domain = random.choice(MOCK_REFERRER_DOMAINS)
    path_template = random.choice(MOCK_DEAD_PATHS)
    slug = _generate_slug()
    dead_path = path_template.format(slug=slug)

    # Generate a realistic target URL that's now broken
    target_paths = [
        f"/blog/{_generate_slug()}",
        f"/resources/{_generate_slug()}",
        f"/guides/{_generate_slug()}",
        f"/posts/{_generate_slug()}",
        f"/{_generate_slug()}"
    ]
    target_path = random.choice(target_paths)

    # Domain rank (higher = more authoritative)
    domain_rank = random.randint(40, 95)

    # Anchor text variations
    anchor_options = [
        f"Read more about {slug.replace('-', ' ')}",
        f"{target_domain}",
        f"Source: {target_domain}",
        f"via {target_domain}",
        f"Learn more",
        f"Click here",
        f"Original article",
        f"{slug.replace('-', ' ').title()}",
        f"this guide",
        f"this resource"
    ]

    return {
        "referring_domain": referrer_domain,
        "referring_url": f"https://{referrer_domain}{dead_path}",
        "target_url": f"https://{target_domain}{target_path}",
        "anchor_text": random.choice(anchor_options),
        "domain_rank": domain_rank,
        "is_dofollow": random.random() > 0.3,  # 70% dofollow
        "first_seen": f"202{random.randint(0, 3)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        "http_code": random.choice([404, 404, 404, 410, 500, 502])  # Most are 404
    }


def _generate_mock_results(domain: str) -> Tuple[List[Dict], int, int]:
    """
    Generate realistic mock broken backlink data for a domain

    Returns: (broken_backlinks, broken_count, total_count)
    """
    # Use domain as seed for consistent results
    seed = _generate_seed(domain)
    random.seed(seed)

    # Generate number of broken backlinks
    broken_count = random.randint(RECLAIM_MIN_BROKEN, RECLAIM_MAX_BROKEN)

    # Total backlinks is higher than broken
    total_count = broken_count + random.randint(200, 800)

    # Generate broken backlinks
    broken_backlinks = []
    used_referrers = set()

    for _ in range(broken_count):
        backlink = _generate_mock_backlink(domain)

        # Ensure some variety in referrer domains
        attempts = 0
        while backlink["referring_domain"] in used_referrers and attempts < 5:
            backlink = _generate_mock_backlink(domain)
            attempts += 1

        used_referrers.add(backlink["referring_domain"])
        broken_backlinks.append(backlink)

    # Sort by domain rank (highest first)
    broken_backlinks.sort(key=lambda x: x["domain_rank"], reverse=True)

    # Reset random seed
    random.seed()

    return broken_backlinks, broken_count, total_count


class DataForSEOClient:
    """Client for DataForSEO Backlinks API with mock data fallback"""

    def __init__(self):
        self.login = DATAFORSEO_LOGIN
        self.password = DATAFORSEO_PASSWORD
        self.use_mock = USE_MOCK_DATA
        self.base_url = "https://api.dataforseo.com/v3"

    def _get_auth_header(self) -> str:
        """Get base64 encoded auth header"""
        credentials = f"{self.login}:{self.password}"
        return base64.b64encode(credentials.encode()).decode()

    def _request(self, endpoint: str, data: List[Dict]) -> Dict:
        """Make authenticated request to DataForSEO API"""
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Basic {self._get_auth_header()}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"DataForSEO API error: {e}")
            return {"status_code": 500, "status_message": str(e)}

    def get_broken_backlinks(self, domain: str) -> Tuple[List[Dict], int, int, int, Optional[str]]:
        """
        Get broken backlinks for a domain

        Tries real DataForSEO API first, falls back to mock data on failure.

        Returns: (broken_backlinks, broken_count, total_count, api_cost_cents, error_message)
        """
        # Clean domain (remove protocol and www)
        parsed = urlparse(domain if "://" in domain else f"https://{domain}")
        clean_domain = parsed.netloc or parsed.path
        clean_domain = clean_domain.replace("www.", "")

        # Try real API first if credentials are configured
        if not self.use_mock:
            result = self._fetch_from_api(clean_domain)
            if result is not None:
                return result
            # API failed - fall through to mock data
            print(f"DataForSEO API failed for {clean_domain}, using mock data")

        # Use mock data (either no credentials or API failed)
        backlinks, broken_count, total_count = _generate_mock_results(clean_domain)
        return backlinks, broken_count, total_count, 0, None

    def _fetch_from_api(self, clean_domain: str) -> Optional[Tuple[List[Dict], int, int, int, Optional[str]]]:
        """
        Fetch broken backlinks from DataForSEO API

        Returns None on failure, allowing caller to fall back to mock data
        """
        # DataForSEO backlinks/backlinks endpoint with filter for broken pages
        # We look for backlinks where the target page returns 4xx or 5xx status
        data = [{
            "target": clean_domain,
            "mode": "as_is",
            "filters": [
                ["page_from_status_code", ">=", 200],
                "and",
                [
                    ["page_to_status_code", ">=", 400],
                    "or",
                    ["page_to_status_code", "=", 0]
                ]
            ],
            "limit": 100,
            "order_by": ["rank,desc"]
        }]

        result = self._request("backlinks/backlinks/live", data)

        # Check for API-level errors
        if result.get("status_code") != 20000:
            error_msg = result.get("status_message", "Unknown API error")
            print(f"DataForSEO API error: {error_msg}")
            return None

        # Parse response
        tasks = result.get("tasks", [])
        if not tasks:
            return [], 0, 0, 0, None

        task = tasks[0]

        # Check task-level status
        task_status = task.get("status_code")
        if task_status != 20000:
            error_msg = task.get("status_message", "Task failed")
            print(f"DataForSEO task error: {error_msg}")
            return None

        api_cost = int(float(task.get("cost", 0)) * 100)  # Convert to cents
        result_data = task.get("result", [])

        if not result_data:
            # No results but API succeeded - domain may have no broken backlinks
            return [], 0, 0, api_cost, None

        first_result = result_data[0]
        items = first_result.get("items", []) or []
        total_count = first_result.get("total_count", 0)

        # Transform API response to our format
        broken_backlinks = []
        for item in items:
            # Extract HTTP status code from page_to_status_code
            http_code = item.get("page_to_status_code", 404)
            if http_code == 0:
                http_code = 404  # Treat unreachable as 404

            # Get first_seen date and format it
            first_seen = item.get("first_seen", "")
            if first_seen and "T" in first_seen:
                first_seen = first_seen.split("T")[0]  # Just the date part

            broken_backlinks.append({
                "referring_domain": item.get("domain_from", ""),
                "referring_url": item.get("url_from", ""),
                "target_url": item.get("url_to", ""),
                "anchor_text": item.get("anchor", "") or "No anchor text",
                "domain_rank": item.get("rank", 0) or item.get("domain_from_rank", 0),
                "is_dofollow": item.get("dofollow", False),
                "first_seen": first_seen,
                "http_code": http_code
            })

        # Sort by domain rank (highest authority first)
        broken_backlinks.sort(key=lambda x: x.get("domain_rank", 0), reverse=True)

        return broken_backlinks, len(broken_backlinks), total_count, api_cost, None

    def get_top_referrers(self, backlinks: List[Dict], limit: int = 5) -> List[Dict]:
        """Extract top referring domains from backlinks list"""
        domain_stats = {}

        for bl in backlinks:
            domain = bl.get("referring_domain", "")
            if domain not in domain_stats:
                domain_stats[domain] = {
                    "domain": domain,
                    "count": 0,
                    "max_rank": 0,
                    "dofollow_count": 0
                }

            domain_stats[domain]["count"] += 1
            domain_stats[domain]["max_rank"] = max(
                domain_stats[domain]["max_rank"],
                bl.get("domain_rank", 0)
            )
            if bl.get("is_dofollow"):
                domain_stats[domain]["dofollow_count"] += 1

        # Sort by max rank (authority)
        top = sorted(
            domain_stats.values(),
            key=lambda x: x["max_rank"],
            reverse=True
        )[:limit]

        return top
