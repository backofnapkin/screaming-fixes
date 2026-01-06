"""
Rank Math SEO Plugin Client.

Provides integration with Rank Math's REST API for:
- Creating and managing redirects
- Updating SEO meta tags (title, description)
"""

from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from wordpress_client import WordPressClient


class RankMathClient:
    """
    Client for Rank Math SEO plugin REST API.

    Rank Math provides comprehensive SEO features including:
    - 301/302/307 redirects
    - SEO meta tags (title, description)
    - Open Graph / Twitter cards
    - Schema markup

    Usage:
        from wordpress_client import WordPressClient

        wp_client = WordPressClient(url, user, pass)
        rm_client = RankMathClient(wp_client)

        # Create a redirect
        rm_client.create_redirect("/old-page/", "/new-page/", redirect_type=301)

        # Update meta tags
        rm_client.update_meta(post_id=123, title="New Title", description="New desc")
    """

    API_BASE = "/wp-json/rankmath/v1"

    def __init__(self, wordpress_client: "WordPressClient"):
        """
        Initialize the Rank Math client.

        Args:
            wordpress_client: An authenticated WordPressClient instance
        """
        self.wp_client = wordpress_client
        self.site_url = wordpress_client.credentials.site_url.rstrip('/')

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
        Make an authenticated request to Rank Math API.

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
                return {"success": False, "error": "Permission denied - check user capabilities"}
            elif response.status_code == 404:
                return {"success": False, "error": "Endpoint not found - is Rank Math installed?"}
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("message", f"HTTP {response.status_code}")
                return {"success": False, "error": error_msg}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Redirect Management
    # =========================================================================

    def create_redirect(
        self,
        source: str,
        target: str,
        redirect_type: int = 301,
        status: str = "active"
    ) -> Dict[str, Any]:
        """
        Create a redirect rule.

        Args:
            source: Source URL path (e.g., "/old-page/" or full URL)
            target: Target URL (can be full URL or relative path)
            redirect_type: HTTP status code (301, 302, 307, 410, 451)
            status: "active" or "inactive"

        Returns:
            Dict with success status and created redirect data
        """
        # Clean up source URL - Rank Math expects just the path
        source_path = source
        if source.startswith(self.site_url):
            source_path = source[len(self.site_url):]
        if not source_path.startswith('/'):
            source_path = '/' + source_path

        data = {
            "url_to_redirect": source_path,
            "redirection_url": target,
            "redirection_type": str(redirect_type),
            "status": status,
        }

        result = self._request("POST", "redirections", data)

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
        per_page: int = 100,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get list of redirects.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page (max 100)
            status: Filter by status ("active", "inactive")

        Returns:
            Dict with success status and list of redirects
        """
        params = {
            "page": page,
            "per_page": min(per_page, 100),
        }
        if status:
            params["status"] = status

        result = self._request("GET", "redirections", params=params)

        if result["success"]:
            redirects = result.get("data", [])
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
        Delete a redirect by ID.

        Args:
            redirect_id: The redirect ID to delete

        Returns:
            Dict with success status
        """
        result = self._request("DELETE", f"redirections/{redirect_id}")

        if result["success"]:
            return {
                "success": True,
                "message": f"Deleted redirect #{redirect_id}",
            }
        else:
            return {
                "success": False,
                "message": f"Failed to delete redirect: {result.get('error')}",
                "error": result.get("error"),
            }

    def bulk_create_redirects(
        self,
        redirects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create multiple redirects at once.

        Args:
            redirects: List of dicts with 'source', 'target', and optionally 'type'
                       Example: [{"source": "/old/", "target": "/new/", "type": 301}]

        Returns:
            Dict with success counts and any errors
        """
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
    # Meta Tag Management
    # =========================================================================

    def update_meta(
        self,
        post_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        focus_keyword: Optional[str] = None,
        robots: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """
        Update SEO meta tags for a post.

        Args:
            post_id: WordPress post ID
            title: SEO title (overrides default)
            description: Meta description
            focus_keyword: Primary focus keyword
            robots: Robot meta settings, e.g., {"noindex": True, "nofollow": False}

        Returns:
            Dict with success status
        """
        # Rank Math stores SEO data as post meta
        # We need to use the WordPress REST API to update post meta
        meta_data = {}

        if title is not None:
            meta_data["rank_math_title"] = title

        if description is not None:
            meta_data["rank_math_description"] = description

        if focus_keyword is not None:
            meta_data["rank_math_focus_keyword"] = focus_keyword

        if robots is not None:
            # Build robots meta string
            robots_parts = []
            if robots.get("noindex"):
                robots_parts.append("noindex")
            if robots.get("nofollow"):
                robots_parts.append("nofollow")
            if robots_parts:
                meta_data["rank_math_robots"] = ",".join(robots_parts)

        if not meta_data:
            return {
                "success": False,
                "message": "No meta data provided to update",
            }

        # Update via WordPress REST API
        # Try posts endpoint first, then pages
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
                error_data = response.json() if response.text else {}
                return {
                    "success": False,
                    "message": f"Failed to update meta: {error_data.get('message', response.status_code)}",
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error updating meta: {str(e)}",
            }

    def get_meta(self, post_id: int) -> Dict[str, Any]:
        """
        Get current SEO meta data for a post.

        Args:
            post_id: WordPress post ID

        Returns:
            Dict with meta data
        """
        # Get post with meta
        url = f"{self.site_url}/wp-json/wp/v2/posts/{post_id}"
        try:
            response = self.wp_client.client.get(url, params={"context": "edit"})

            if response.status_code == 404:
                url = f"{self.site_url}/wp-json/wp/v2/pages/{post_id}"
                response = self.wp_client.client.get(url, params={"context": "edit"})

            if response.status_code == 200:
                post_data = response.json()
                meta = post_data.get("meta", {})

                return {
                    "success": True,
                    "meta": {
                        "title": meta.get("rank_math_title", ""),
                        "description": meta.get("rank_math_description", ""),
                        "focus_keyword": meta.get("rank_math_focus_keyword", ""),
                        "robots": meta.get("rank_math_robots", ""),
                    },
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
    # Utility Methods
    # =========================================================================

    def test_connection(self) -> Dict[str, Any]:
        """Test that Rank Math API is accessible"""
        result = self._request("GET", "")

        if result["success"]:
            return {
                "success": True,
                "message": "Rank Math API is accessible",
            }
        else:
            return {
                "success": False,
                "message": f"Rank Math API not accessible: {result.get('error')}",
            }
