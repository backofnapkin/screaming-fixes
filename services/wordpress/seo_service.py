"""
Unified SEO Service for WordPress.

Provides a single interface for SEO operations that automatically
uses the best available plugin for each operation.
"""

from typing import Dict, List, Optional, Any, TYPE_CHECKING

from .plugin_detector import PluginDetector, DetectedPlugin, PluginCapability
from .rank_math import RankMathClient
from .redirection import RedirectionClient
from .yoast import YoastClient

if TYPE_CHECKING:
    from wordpress_client import WordPressClient


class NoCapablePluginError(Exception):
    """Raised when no installed plugin can handle the requested operation"""

    def __init__(self, capability: str, message: str = None):
        self.capability = capability
        self.message = message or f"No plugin installed that supports {capability}"
        super().__init__(self.message)


class SEOService:
    """
    Unified SEO service that abstracts over multiple WordPress SEO plugins.

    This service:
    1. Detects which SEO plugins are installed
    2. Automatically uses the best available plugin for each operation
    3. Provides a consistent API regardless of which plugin is used

    Usage:
        from wordpress_client import WordPressClient
        from services.wordpress import SEOService

        wp_client = WordPressClient(url, user, pass)
        seo = SEOService(wp_client)

        # Check capabilities
        if seo.can_create_redirects:
            seo.create_redirect("/old/", "/new/")

        if seo.can_update_meta:
            seo.update_meta(123, title="New Title", description="Desc")

        # Get detection summary for UI
        summary = seo.get_summary()
    """

    def __init__(
        self,
        wordpress_client: "WordPressClient",
        auto_detect: bool = True
    ):
        """
        Initialize the SEO service.

        Args:
            wordpress_client: An authenticated WordPressClient instance
            auto_detect: Whether to run plugin detection immediately
        """
        self.wp_client = wordpress_client
        self.detector = PluginDetector(wordpress_client)

        # Plugin clients (lazily initialized)
        self._rank_math: Optional[RankMathClient] = None
        self._redirection: Optional[RedirectionClient] = None
        self._yoast: Optional[YoastClient] = None

        # Cached handlers
        self._redirect_handler: Optional[DetectedPlugin] = None
        self._meta_handler: Optional[DetectedPlugin] = None

        if auto_detect:
            self.detect_plugins()

    def detect_plugins(self, force: bool = False) -> List[DetectedPlugin]:
        """
        Detect installed SEO plugins.

        Args:
            force: Re-run detection even if already complete

        Returns:
            List of detected plugins
        """
        plugins = self.detector.detect_all(force=force)

        # Update cached handlers
        self._redirect_handler = self.detector.get_redirect_handler()
        self._meta_handler = self.detector.get_meta_handler()

        return plugins

    # =========================================================================
    # Plugin Client Accessors
    # =========================================================================

    def _get_rank_math(self) -> RankMathClient:
        """Get or create Rank Math client"""
        if self._rank_math is None:
            self._rank_math = RankMathClient(self.wp_client)
        return self._rank_math

    def _get_redirection(self) -> RedirectionClient:
        """Get or create Redirection client"""
        if self._redirection is None:
            self._redirection = RedirectionClient(self.wp_client)
        return self._redirection

    def _get_yoast(self) -> YoastClient:
        """Get or create Yoast client"""
        if self._yoast is None:
            self._yoast = YoastClient(self.wp_client)
        return self._yoast

    # =========================================================================
    # Capability Checks
    # =========================================================================

    @property
    def can_create_redirects(self) -> bool:
        """Check if any installed plugin can create redirects"""
        return self._redirect_handler is not None

    @property
    def can_update_meta(self) -> bool:
        """Check if any installed plugin can update meta tags"""
        return self._meta_handler is not None

    @property
    def redirect_handler_name(self) -> Optional[str]:
        """Get the name of the plugin handling redirects"""
        return self._redirect_handler.name if self._redirect_handler else None

    @property
    def meta_handler_name(self) -> Optional[str]:
        """Get the name of the plugin handling meta tags"""
        return self._meta_handler.name if self._meta_handler else None

    @property
    def detected_plugins(self) -> List[DetectedPlugin]:
        """Get list of all detected plugins"""
        return self.detector.detect_all()

    # =========================================================================
    # Redirect Operations
    # =========================================================================

    def create_redirect(
        self,
        source: str,
        target: str,
        redirect_type: int = 301
    ) -> Dict[str, Any]:
        """
        Create a redirect using the best available plugin.

        Args:
            source: Source URL path
            target: Target URL
            redirect_type: HTTP status code (301, 302, etc.)

        Returns:
            Dict with success status and details

        Raises:
            NoCapablePluginError: If no plugin can handle redirects
        """
        if not self.can_create_redirects:
            raise NoCapablePluginError(
                "redirects",
                "No SEO plugin installed that supports redirects. "
                "Install Rank Math or Redirection plugin to enable this feature."
            )

        handler = self._redirect_handler

        if handler.slug == "rank_math":
            client = self._get_rank_math()
            result = client.create_redirect(source, target, redirect_type)
        elif handler.slug == "redirection":
            client = self._get_redirection()
            result = client.create_redirect(source, target, redirect_type)
        elif handler.slug == "yoast":
            client = self._get_yoast()
            result = client.create_redirect(source, target, redirect_type)
        else:
            raise NoCapablePluginError(
                "redirects",
                f"Unknown redirect handler: {handler.slug}"
            )

        result["handler"] = handler.name
        return result

    def bulk_create_redirects(
        self,
        redirects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create multiple redirects at once.

        Args:
            redirects: List of dicts with 'source', 'target', and optionally 'type'

        Returns:
            Dict with success counts

        Raises:
            NoCapablePluginError: If no plugin can handle redirects
        """
        if not self.can_create_redirects:
            raise NoCapablePluginError(
                "redirects",
                "No SEO plugin installed that supports redirects."
            )

        handler = self._redirect_handler

        if handler.slug == "rank_math":
            client = self._get_rank_math()
            result = client.bulk_create_redirects(redirects)
        elif handler.slug == "redirection":
            client = self._get_redirection()
            result = client.bulk_create_redirects(redirects)
        elif handler.slug == "yoast":
            client = self._get_yoast()
            result = client.bulk_create_redirects(redirects)
        else:
            raise NoCapablePluginError("redirects", f"Unknown handler: {handler.slug}")

        result["handler"] = handler.name
        return result

    def get_redirects(self) -> Dict[str, Any]:
        """
        Get list of existing redirects.

        Returns:
            Dict with list of redirects

        Raises:
            NoCapablePluginError: If no plugin can handle redirects
        """
        if not self.can_create_redirects:
            raise NoCapablePluginError("redirects")

        handler = self._redirect_handler

        if handler.slug == "rank_math":
            return self._get_rank_math().get_redirects()
        elif handler.slug == "redirection":
            return self._get_redirection().get_redirects()
        elif handler.slug == "yoast":
            return self._get_yoast().get_redirects()
        else:
            raise NoCapablePluginError("redirects", f"Unknown handler: {handler.slug}")

    # =========================================================================
    # Meta Tag Operations
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
        Update SEO meta tags for a post using the best available plugin.

        Args:
            post_id: WordPress post ID
            title: SEO title
            description: Meta description
            focus_keyword: Primary focus keyword
            robots: Robot meta settings, e.g., {"noindex": True}

        Returns:
            Dict with success status

        Raises:
            NoCapablePluginError: If no plugin can handle meta tags
        """
        if not self.can_update_meta:
            raise NoCapablePluginError(
                "meta_tags",
                "No SEO plugin installed that supports meta tags. "
                "Install Rank Math or Yoast SEO to enable this feature."
            )

        handler = self._meta_handler

        if handler.slug == "rank_math":
            client = self._get_rank_math()
            result = client.update_meta(
                post_id,
                title=title,
                description=description,
                focus_keyword=focus_keyword,
                robots=robots
            )
        elif handler.slug == "yoast":
            client = self._get_yoast()
            result = client.update_meta(
                post_id,
                title=title,
                description=description,
                focus_keyword=focus_keyword,
                robots=robots
            )
        else:
            raise NoCapablePluginError(
                "meta_tags",
                f"Unknown meta handler: {handler.slug}"
            )

        result["handler"] = handler.name
        return result

    def get_meta(self, post_id: int) -> Dict[str, Any]:
        """
        Get current SEO meta data for a post.

        Args:
            post_id: WordPress post ID

        Returns:
            Dict with meta data

        Raises:
            NoCapablePluginError: If no plugin can handle meta tags
        """
        if not self.can_update_meta:
            raise NoCapablePluginError("meta_tags")

        handler = self._meta_handler

        if handler.slug == "rank_math":
            return self._get_rank_math().get_meta(post_id)
        elif handler.slug == "yoast":
            return self._get_yoast().get_meta(post_id)
        else:
            raise NoCapablePluginError("meta_tags", f"Unknown handler: {handler.slug}")

    # =========================================================================
    # Summary and UI Helpers
    # =========================================================================

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of detected plugins and capabilities.

        Useful for displaying in the UI.

        Returns:
            Dict with plugin info and capability status
        """
        return self.detector.get_detection_summary()

    def get_capability_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed capability status for UI display.

        Returns:
            Dict with capability names as keys and status info as values
        """
        return {
            "redirects": {
                "available": self.can_create_redirects,
                "handler": self.redirect_handler_name,
                "icon": "check" if self.can_create_redirects else "x",
                "status_text": (
                    f"Using {self.redirect_handler_name}"
                    if self.can_create_redirects
                    else "Install Rank Math or Redirection plugin"
                ),
            },
            "meta_tags": {
                "available": self.can_update_meta,
                "handler": self.meta_handler_name,
                "icon": "check" if self.can_update_meta else "x",
                "status_text": (
                    f"Using {self.meta_handler_name}"
                    if self.can_update_meta
                    else "Install Rank Math or Yoast SEO"
                ),
            },
        }

    def get_missing_capabilities_message(self) -> Optional[str]:
        """
        Get a user-friendly message about missing capabilities.

        Returns:
            Message string if capabilities are missing, None if all available
        """
        missing = []

        if not self.can_create_redirects:
            missing.append("redirects")

        if not self.can_update_meta:
            missing.append("meta tags")

        if not missing:
            return None

        if len(missing) == 1:
            capability = missing[0]
            if capability == "redirects":
                return (
                    "Install Rank Math or Redirection plugin to enable "
                    "automatic redirect creation for broken links."
                )
            else:
                return (
                    "Install Rank Math or Yoast SEO to enable "
                    "automatic meta tag updates."
                )
        else:
            return (
                "Install Rank Math to enable both redirect creation "
                "and meta tag updates, or install individual plugins "
                "(Redirection for redirects, Yoast for meta tags)."
            )
