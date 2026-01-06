"""
Yoast SEO Plugin Client.

Provides integration with Yoast SEO's REST API for:
- Updating SEO meta tags (title, description)
- Creating redirects (Premium version only)
"""

from typing import Dict, Optional, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from wordpress_client import WordPressClient


class YoastClient:
    """
    Client for Yoast SEO plugin REST API.

    Yoast SEO is one of the most popular WordPress SEO plugins.
    The free version supports:
    - SEO meta tags (title, description)
    - Open Graph / Twitter cards
    - Schema markup
    - Sitemaps

    Yoast Premium adds:
    - Redirect manager
    - Internal linking suggestions
    - Multiple focus keywords

    Usage:
        from wordpress_client import WordPressClient

        wp_client = WordPressClient(url, user, pass)
        yoast_client = YoastClient(wp_client)

        # Update meta tags (free version)
        yoast_client.update_meta(post_id=123, title="New Title", description="Desc")

        # Create redirect (Premium only)
        if yoast_client.has_premium:
            yoast_client.create_redirect("/old/", "/new/")
    """

    API_BASE = "/wp-json/yoast/v1"

    def __init__(self, wordpress_client: "WordPressClient"):
        """
        Initialize the Yoast client.

        Args:
            wordpress_client: An authenticated WordPressClient instance
        """
        self.wp_client = wordpress_client
        self.site_url = wordpress_client.credentials.site_url.rstrip('/')
        self._has_premium = None

    def _get_url(self, endpoint: str) -> str:
        """Build full URL for an endpoint"""
        return f"{self.site_url}{self.API_BASE}/{endpoint.lstrip('/')}"

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make an authenticated request to Yoast API.

        Returns:
            Dict with 'success', 'data', and optionally 'error'
        """
        url = self._get_url(endpoint)

        try:
            if method.upper() == "GET":
                response = self.wp_client.client.get(url, params=params)
            elif method.upper() == "POST":
                response = self.wp_client.client.post(url, json=data)
            elif method.upper() == "PUT":
                response = self.wp_client.client.put(url, json=data)
            elif method.upper() == "DELETE":
                response = self.wp_client.client.delete(url, params=params)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}

            if response.status_code in (200, 201):
                return {"success": True, "data": response.json()}
            elif response.status_code == 204:
                return {"success": True, "data": None}
            elif response.status_code == 401:
                return {"success": False, "error": "Authentication failed"}
            elif response.status_code == 403:
                return {"success": False, "error": "Permission denied"}
            elif response.status_code == 404:
                return {"success": False, "error": "Endpoint not found"}
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", f"HTTP {response.status_code}")
                except Exception:
                    error_msg = f"HTTP {response.status_code}"
                return {"success": False, "error": error_msg}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @property
    def has_premium(self) -> bool:
        """Check if Yoast Premium is installed (has redirect capabilities)"""
        if self._has_premium is None:
            # Try to access the redirects endpoint
            url = self._get_url("redirects")
            try:
                response = self.wp_client.client.get(url)
                # If we get anything other than 404, Premium is installed
                self._has_premium = response.status_code != 404
            except Exception:
                self._has_premium = False
        return self._has_premium

    # =========================================================================
    # Meta Tag Management
    # =========================================================================

    def update_meta(
        self,
        post_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        focus_keyword: Optional[str] = None,
        og_title: Optional[str] = None,
        og_description: Optional[str] = None,
        twitter_title: Optional[str] = None,
        twitter_description: Optional[str] = None,
        canonical: Optional[str] = None,
        robots: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """
        Update SEO meta tags for a post.

        Yoast stores SEO data as post meta with _yoast_wpseo_ prefix.

        Args:
            post_id: WordPress post ID
            title: SEO title
            description: Meta description
            focus_keyword: Primary focus keyword
            og_title: Open Graph title
            og_description: Open Graph description
            twitter_title: Twitter card title
            twitter_description: Twitter card description
            canonical: Canonical URL
            robots: Robot meta settings, e.g., {"noindex": True}

        Returns:
            Dict with success status
        """
        meta_data = {}

        if title is not None:
            meta_data["_yoast_wpseo_title"] = title

        if description is not None:
            meta_data["_yoast_wpseo_metadesc"] = description

        if focus_keyword is not None:
            meta_data["_yoast_wpseo_focuskw"] = focus_keyword

        if og_title is not None:
            meta_data["_yoast_wpseo_opengraph-title"] = og_title

        if og_description is not None:
            meta_data["_yoast_wpseo_opengraph-description"] = og_description

        if twitter_title is not None:
            meta_data["_yoast_wpseo_twitter-title"] = twitter_title

        if twitter_description is not None:
            meta_data["_yoast_wpseo_twitter-description"] = twitter_description

        if canonical is not None:
            meta_data["_yoast_wpseo_canonical"] = canonical

        if robots is not None:
            # Yoast uses separate meta keys for robot settings
            if robots.get("noindex"):
                meta_data["_yoast_wpseo_meta-robots-noindex"] = "1"
            if robots.get("nofollow"):
                meta_data["_yoast_wpseo_meta-robots-nofollow"] = "1"

        if not meta_data:
            return {
                "success": False,
                "message": "No meta data provided to update",
            }

        # Update via WordPress REST API
        update_url = f"{self.site_url}/wp-json/wp/v2/posts/{post_id}"
        try:
            response = self.wp_client.client.post(
                update_url,
                json={"meta": meta_data}
            )

            if response.status_code == 404:
                # Try pages
                update_url = f"{self.site_url}/wp-json/wp/v2/pages/{post_id}"
                response = self.wp_client.client.post(
                    update_url,
                    json={"meta": meta_data}
                )

            if response.status_code in (200, 201):
                return {
                    "success": True,
                    "message": f"Updated meta for post #{post_id}",
                    "updated_fields": list(meta_data.keys()),
                }
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", f"HTTP {response.status_code}")
                except Exception:
                    error_msg = f"HTTP {response.status_code}"
                return {
                    "success": False,
                    "message": f"Failed to update meta: {error_msg}",
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating meta: {str(e)}",
            }

    def get_meta(self, post_id: int) -> Dict[str, Any]:
        """
        Get current Yoast SEO meta data for a post.

        Args:
            post_id: WordPress post ID

        Returns:
            Dict with meta data
        """
        url = f"{self.site_url}/wp-json/wp/v2/posts/{post_id}"
        try:
            response = self.wp_client.client.get(url, params={"context": "edit"})

            if response.status_code == 404:
                url = f"{self.site_url}/wp-json/wp/v2/pages/{post_id}"
                response = self.wp_client.client.get(url, params={"context": "edit"})

            if response.status_code == 200:
                post_data = response.json()
                meta = post_data.get("meta", {})
                yoast_head = post_data.get("yoast_head_json", {})

                return {
                    "success": True,
                    "meta": {
                        "title": meta.get("_yoast_wpseo_title", ""),
                        "description": meta.get("_yoast_wpseo_metadesc", ""),
                        "focus_keyword": meta.get("_yoast_wpseo_focuskw", ""),
                        "canonical": meta.get("_yoast_wpseo_canonical", ""),
                        "og_title": meta.get("_yoast_wpseo_opengraph-title", ""),
                        "og_description": meta.get("_yoast_wpseo_opengraph-description", ""),
                    },
                    "yoast_head": yoast_head,
                }
            else:
                return {
                    "success": False,
                    "error": f"Could not fetch post #{post_id}",
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # Redirect Management (Premium Only)
    # =========================================================================

    def create_redirect(
        self,
        source: str,
        target: str,
        redirect_type: int = 301,
        format: str = "plain"
    ) -> Dict[str, Any]:
        """
        Create a redirect rule (Yoast Premium only).

        Args:
            source: Source URL path
            target: Target URL
            redirect_type: HTTP status code (301, 302, 307, 410, 451)
            format: Match format ("plain" or "regex")

        Returns:
            Dict with success status
        """
        if not self.has_premium:
            return {
                "success": False,
                "message": "Redirects require Yoast SEO Premium",
                "error": "premium_required",
            }

        # Clean up source URL
        source_path = source
        if source.startswith(self.site_url):
            source_path = source[len(self.site_url):]
        if not source_path.startswith('/'):
            source_path = '/' + source_path

        data = {
            "origin": source_path,
            "target": target,
            "type": redirect_type,
            "format": format,
        }

        result = self._request("POST", "redirects", data)

        if result["success"]:
            return {
                "success": True,
                "message": f"Created {redirect_type} redirect: {source_path} → {target}",
                "redirect_id": result["data"].get("id") if result.get("data") else None,
                "data": result.get("data"),
            }
        else:
            return {
                "success": False,
                "message": f"Failed to create redirect: {result.get('error')}",
                "error": result.get("error"),
            }

    def get_redirects(
        self,
        page: int = 1,
        per_page: int = 100
    ) -> Dict[str, Any]:
        """
        Get list of redirects (Yoast Premium only).

        Args:
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Dict with list of redirects
        """
        if not self.has_premium:
            return {
                "success": False,
                "redirects": [],
                "error": "Redirects require Yoast SEO Premium",
            }

        params = {
            "page": page,
            "per_page": per_page,
        }

        result = self._request("GET", "redirects", params=params)

        if result["success"]:
            redirects = result.get("data", [])
            if isinstance(redirects, dict):
                redirects = redirects.get("redirects", [])

            return {
                "success": True,
                "redirects": redirects,
                "count": len(redirects),
            }
        else:
            return {
                "success": False,
                "redirects": [],
                "error": result.get("error"),
            }

    def delete_redirect(self, redirect_id: int) -> Dict[str, Any]:
        """
        Delete a redirect (Yoast Premium only).

        Args:
            redirect_id: The redirect ID to delete

        Returns:
            Dict with success status
        """
        if not self.has_premium:
            return {
                "success": False,
                "message": "Redirects require Yoast SEO Premium",
            }

        result = self._request("DELETE", f"redirects/{redirect_id}")

        if result["success"]:
            return {
                "success": True,
                "message": f"Deleted redirect #{redirect_id}",
            }
        else:
            return {
                "success": False,
                "message": f"Failed to delete redirect: {result.get('error')}",
            }

    def bulk_create_redirects(
        self,
        redirects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create multiple redirects at once (Yoast Premium only).

        Args:
            redirects: List of dicts with 'source', 'target', and optionally 'type'

        Returns:
            Dict with success counts
        """
        if not self.has_premium:
            return {
                "success": False,
                "created": 0,
                "failed": len(redirects),
                "errors": ["Redirects require Yoast SEO Premium"],
            }

        results = {
            "success": True,
            "created": 0,
            "failed": 0,
            "errors": [],
        }

        for redirect in redirects:
            source = redirect.get("source", "")
            target = redirect.get("target", "")
            redirect_type = redirect.get("type", 301)

            if not source or not target:
                results["failed"] += 1
                results["errors"].append(f"Invalid redirect: {redirect}")
                continue

            result = self.create_redirect(source, target, redirect_type)

            if result["success"]:
                results["created"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"{source}: {result.get('error')}")

        results["success"] = results["failed"] == 0
        return results

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def test_connection(self) -> Dict[str, Any]:
        """Test that Yoast API is accessible"""
        # Try the main Yoast endpoint
        url = f"{self.site_url}{self.API_BASE}/"
        try:
            response = self.wp_client.client.get(url)
            if response.status_code != 404:
                premium_status = "Premium" if self.has_premium else "Free"
                return {
                    "success": True,
                    "message": f"Yoast SEO ({premium_status}) is accessible",
                    "has_premium": self.has_premium,
                }
            else:
                return {
                    "success": False,
                    "message": "Yoast SEO API not found - is Yoast installed?",
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error testing Yoast: {str(e)}",
            }
