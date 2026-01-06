"""
Redirection Plugin Client.

Provides integration with the Redirection plugin's REST API for
creating and managing URL redirects.
"""

from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from wordpress_client import WordPressClient


class RedirectionClient:
    """
    Client for Redirection plugin REST API.

    The Redirection plugin is a popular, free WordPress plugin
    specifically for managing redirects. It supports:
    - 301, 302, 303, 304, 307, 308 redirects
    - Pass-through redirects
    - 404 error logging
    - Import/export functionality

    Usage:
        from wordpress_client import WordPressClient

        wp_client = WordPressClient(url, user, pass)
        redir_client = RedirectionClient(wp_client)

        # Create a redirect
        redir_client.create_redirect("/old-page/", "/new-page/")

        # Bulk create
        redir_client.bulk_create_redirects([
            {"source": "/old-1/", "target": "/new-1/"},
            {"source": "/old-2/", "target": "/new-2/"},
        ])
    """

    API_BASE = "/wp-json/redirection/v1"

    # Redirect action types
    ACTION_URL = "url"  # Redirect to URL
    ACTION_RANDOM = "random"  # Redirect to random post
    ACTION_PASS = "pass"  # Pass-through
    ACTION_ERROR = "error"  # Custom error page
    ACTION_NOTHING = "nothing"  # Do nothing

    # Match types
    MATCH_URL = "url"  # Exact URL match
    MATCH_LOGIN = "login"  # URL and login status
    MATCH_ROLE = "role"  # URL and user role
    MATCH_REFERRER = "referrer"  # URL and referrer
    MATCH_AGENT = "agent"  # URL and user agent
    MATCH_COOKIE = "cookie"  # URL and cookie
    MATCH_HEADER = "header"  # URL and HTTP header
    MATCH_CUSTOM = "custom"  # URL and custom filter
    MATCH_PAGE = "page"  # URL and page type

    def __init__(self, wordpress_client: "WordPressClient"):
        """
        Initialize the Redirection client.

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
        Make an authenticated request to Redirection API.

        Returns:
            Dict with 'success', 'data', and optionally 'error'
        """
        url = self._get_url(endpoint)

        try:
            if method.upper() == "GET":
                response = self.wp_client.client.get(url, params=params)
            elif method.upper() == "POST":
                response = self.wp_client.client.post(url, json=data)
            elif method.upper() == "DELETE":
                response = self.wp_client.client.delete(url, params=params)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}

            if response.status_code in (200, 201):
                response_data = response.json()
                # Redirection API wraps responses differently
                if isinstance(response_data, dict):
                    # Check for Redirection's error format
                    if response_data.get("error"):
                        return {
                            "success": False,
                            "error": response_data.get("error", {}).get("message", "Unknown error"),
                        }
                    return {"success": True, "data": response_data}
                return {"success": True, "data": response_data}
            elif response.status_code == 204:
                return {"success": True, "data": None}
            elif response.status_code == 401:
                return {"success": False, "error": "Authentication failed"}
            elif response.status_code == 403:
                return {"success": False, "error": "Permission denied"}
            elif response.status_code == 404:
                return {"success": False, "error": "Endpoint not found - is Redirection plugin installed?"}
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", f"HTTP {response.status_code}")
                except Exception:
                    error_msg = f"HTTP {response.status_code}"
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
        match_type: str = "url",
        action_type: str = "url",
        group_id: int = 1,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Create a redirect rule.

        Args:
            source: Source URL path (regex supported)
            target: Target URL
            redirect_type: HTTP status code (301, 302, 303, 304, 307, 308)
            match_type: How to match the URL (url, login, role, referrer, etc.)
            action_type: What to do when matched (url, random, pass, error, nothing)
            group_id: Redirect group ID (default 1 is "Redirections")
            enabled: Whether redirect is active

        Returns:
            Dict with success status and created redirect data
        """
        # Clean up source - Redirection expects relative paths
        source_path = source
        if source.startswith(self.site_url):
            source_path = source[len(self.site_url):]
        if not source_path.startswith('/'):
            source_path = '/' + source_path

        data = {
            "url": source_path,
            "action_data": {
                "url": target,
            },
            "action_type": action_type,
            "action_code": redirect_type,
            "match_type": match_type,
            "group_id": group_id,
            "enabled": enabled,
        }

        result = self._request("POST", "redirect", data)

        if result["success"]:
            redirect_data = result.get("data", {}).get("item", result.get("data", {}))
            return {
                "success": True,
                "message": f"Created {redirect_type} redirect: {source_path} → {target}",
                "redirect_id": redirect_data.get("id"),
                "data": redirect_data,
            }
        else:
            return {
                "success": False,
                "message": f"Failed to create redirect: {result.get('error')}",
                "error": result.get("error"),
            }

    def get_redirects(
        self,
        page: int = 0,
        per_page: int = 100,
        filter_by: Optional[str] = None,
        order_by: str = "id",
        direction: str = "desc"
    ) -> Dict[str, Any]:
        """
        Get list of redirects.

        Args:
            page: Page number (0-indexed)
            per_page: Items per page
            filter_by: Filter string
            order_by: Sort field (id, url, last_access, etc.)
            direction: Sort direction (asc, desc)

        Returns:
            Dict with success status and list of redirects
        """
        params = {
            "page": page,
            "per_page": min(per_page, 200),
            "orderby": order_by,
            "direction": direction,
        }
        if filter_by:
            params["filter"] = filter_by

        result = self._request("GET", "redirect", params=params)

        if result["success"]:
            data = result.get("data", {})
            items = data.get("items", []) if isinstance(data, dict) else data
            total = data.get("total", len(items)) if isinstance(data, dict) else len(items)

            return {
                "success": True,
                "redirects": items,
                "count": len(items),
                "total": total,
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
        data = {
            "items": [redirect_id],
        }
        result = self._request("POST", "bulk/redirect/delete", data)

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

    def update_redirect(
        self,
        redirect_id: int,
        source: Optional[str] = None,
        target: Optional[str] = None,
        redirect_type: Optional[int] = None,
        enabled: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update an existing redirect.

        Args:
            redirect_id: The redirect ID to update
            source: New source URL (optional)
            target: New target URL (optional)
            redirect_type: New redirect type (optional)
            enabled: Enable/disable redirect (optional)

        Returns:
            Dict with success status
        """
        data = {}

        if source is not None:
            source_path = source
            if source.startswith(self.site_url):
                source_path = source[len(self.site_url):]
            if not source_path.startswith('/'):
                source_path = '/' + source_path
            data["url"] = source_path

        if target is not None:
            data["action_data"] = {"url": target}

        if redirect_type is not None:
            data["action_code"] = redirect_type

        if enabled is not None:
            data["enabled"] = enabled

        if not data:
            return {
                "success": False,
                "message": "No update data provided",
            }

        # Redirection uses POST with ID in data for updates
        data["id"] = redirect_id
        result = self._request("POST", "redirect", data)

        if result["success"]:
            return {
                "success": True,
                "message": f"Updated redirect #{redirect_id}",
            }
        else:
            return {
                "success": False,
                "message": f"Failed to update redirect: {result.get('error')}",
                "error": result.get("error"),
            }

    def enable_redirect(self, redirect_id: int) -> Dict[str, Any]:
        """Enable a redirect"""
        return self.update_redirect(redirect_id, enabled=True)

    def disable_redirect(self, redirect_id: int) -> Dict[str, Any]:
        """Disable a redirect"""
        return self.update_redirect(redirect_id, enabled=False)

    # =========================================================================
    # Groups Management
    # =========================================================================

    def get_groups(self) -> Dict[str, Any]:
        """
        Get list of redirect groups.

        Returns:
            Dict with list of groups
        """
        result = self._request("GET", "group")

        if result["success"]:
            data = result.get("data", {})
            items = data.get("items", []) if isinstance(data, dict) else []

            return {
                "success": True,
                "groups": items,
            }
        else:
            return {
                "success": False,
                "groups": [],
                "error": result.get("error"),
            }

    # =========================================================================
    # 404 Log
    # =========================================================================

    def get_404_logs(
        self,
        page: int = 0,
        per_page: int = 100
    ) -> Dict[str, Any]:
        """
        Get 404 error logs.

        Args:
            page: Page number (0-indexed)
            per_page: Items per page

        Returns:
            Dict with list of 404 errors
        """
        params = {
            "page": page,
            "per_page": per_page,
        }

        result = self._request("GET", "404", params=params)

        if result["success"]:
            data = result.get("data", {})
            items = data.get("items", []) if isinstance(data, dict) else []

            return {
                "success": True,
                "logs": items,
                "count": len(items),
            }
        else:
            return {
                "success": False,
                "logs": [],
                "error": result.get("error"),
            }

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def test_connection(self) -> Dict[str, Any]:
        """Test that Redirection API is accessible"""
        result = self._request("GET", "plugin")

        if result["success"]:
            return {
                "success": True,
                "message": "Redirection API is accessible",
            }
        else:
            return {
                "success": False,
                "message": f"Redirection API not accessible: {result.get('error')}",
            }
