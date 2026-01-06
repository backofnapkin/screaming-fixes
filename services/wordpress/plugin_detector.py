"""
SEO Plugin Detector for WordPress.

Detects installed SEO plugins by probing their REST API endpoints.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from wordpress_client import WordPressClient


class PluginCapability(Enum):
    """Capabilities that SEO plugins can provide"""
    REDIRECTS = "redirects"
    META_TAGS = "meta_tags"
    SITEMAPS = "sitemaps"
    SCHEMA = "schema"


@dataclass
class DetectedPlugin:
    """Information about a detected SEO plugin"""
    name: str
    slug: str
    version: Optional[str] = None
    is_premium: bool = False
    capabilities: List[PluginCapability] = field(default_factory=list)
    api_base: Optional[str] = None

    def has_capability(self, capability: PluginCapability) -> bool:
        """Check if plugin has a specific capability"""
        return capability in self.capabilities

    @property
    def can_create_redirects(self) -> bool:
        return PluginCapability.REDIRECTS in self.capabilities

    @property
    def can_update_meta(self) -> bool:
        return PluginCapability.META_TAGS in self.capabilities


class PluginDetector:
    """
    Detects SEO plugins installed on a WordPress site.

    Probes REST API endpoints to determine which plugins are active
    and what capabilities they provide.

    Usage:
        from wordpress_client import WordPressClient

        client = WordPressClient(url, user, pass)
        detector = PluginDetector(client)

        plugins = detector.detect_all()
        redirect_handler = detector.get_redirect_handler()
    """

    # Plugin detection configuration
    PLUGIN_ENDPOINTS = {
        "rank_math": {
            "name": "Rank Math",
            "probe_endpoints": [
                "/wp-json/rankmath/v1/",
            ],
            "capabilities": [
                PluginCapability.REDIRECTS,
                PluginCapability.META_TAGS,
                PluginCapability.SITEMAPS,
                PluginCapability.SCHEMA,
            ],
            "api_base": "/wp-json/rankmath/v1",
        },
        "yoast": {
            "name": "Yoast SEO",
            "probe_endpoints": [
                "/wp-json/yoast/v1/",
            ],
            "capabilities": [
                PluginCapability.META_TAGS,
                PluginCapability.SITEMAPS,
                PluginCapability.SCHEMA,
            ],
            "premium_probe": "/wp-json/yoast/v1/redirects",
            "premium_capabilities": [
                PluginCapability.REDIRECTS,
            ],
            "api_base": "/wp-json/yoast/v1",
        },
        "redirection": {
            "name": "Redirection",
            "probe_endpoints": [
                "/wp-json/redirection/v1/",
            ],
            "capabilities": [
                PluginCapability.REDIRECTS,
            ],
            "api_base": "/wp-json/redirection/v1",
        },
        "aioseo": {
            "name": "All in One SEO",
            "probe_endpoints": [
                "/wp-json/aioseo/v1/",
            ],
            "capabilities": [
                PluginCapability.META_TAGS,
                PluginCapability.SITEMAPS,
                PluginCapability.SCHEMA,
            ],
            "premium_probe": "/wp-json/aioseo/v1/redirects",
            "premium_capabilities": [
                PluginCapability.REDIRECTS,
            ],
            "api_base": "/wp-json/aioseo/v1",
        },
        "seopress": {
            "name": "SEOPress",
            "probe_endpoints": [
                "/wp-json/seopress/v1/",
            ],
            "capabilities": [
                PluginCapability.META_TAGS,
                PluginCapability.SITEMAPS,
            ],
            "api_base": "/wp-json/seopress/v1",
        },
    }

    # Priority order for redirect handlers (best to worst)
    REDIRECT_PRIORITY = ["rank_math", "redirection", "yoast", "aioseo"]

    # Priority order for meta handlers (best to worst)
    META_PRIORITY = ["rank_math", "yoast", "aioseo", "seopress"]

    def __init__(self, wordpress_client: "WordPressClient"):
        """
        Initialize the plugin detector.

        Args:
            wordpress_client: An authenticated WordPressClient instance
        """
        self.wp_client = wordpress_client
        self.site_url = wordpress_client.credentials.site_url.rstrip('/')
        self._detected_plugins: Dict[str, DetectedPlugin] = {}
        self._detection_complete = False

    def _probe_endpoint(self, endpoint: str) -> bool:
        """
        Probe an endpoint to check if it exists.

        Returns True if the endpoint responds (even with 401/403),
        False if it returns 404 or connection fails.
        """
        try:
            url = f"{self.site_url}{endpoint}"
            response = self.wp_client.client.get(url)
            # Any response except 404 means the endpoint exists
            # 401/403 just means auth required, but plugin is installed
            return response.status_code != 404
        except Exception:
            return False

    def _detect_plugin(self, slug: str, config: Dict[str, Any]) -> Optional[DetectedPlugin]:
        """Detect a single plugin by probing its endpoints"""
        # Check main endpoints
        detected = False
        for endpoint in config.get("probe_endpoints", []):
            if self._probe_endpoint(endpoint):
                detected = True
                break

        if not detected:
            return None

        # Build capabilities list
        capabilities = list(config.get("capabilities", []))
        is_premium = False

        # Check for premium features
        premium_probe = config.get("premium_probe")
        if premium_probe and self._probe_endpoint(premium_probe):
            is_premium = True
            capabilities.extend(config.get("premium_capabilities", []))

        return DetectedPlugin(
            name=config["name"],
            slug=slug,
            is_premium=is_premium,
            capabilities=capabilities,
            api_base=config.get("api_base"),
        )

    def detect_all(self, force: bool = False) -> List[DetectedPlugin]:
        """
        Detect all installed SEO plugins.

        Args:
            force: Re-run detection even if already complete

        Returns:
            List of detected plugins
        """
        if self._detection_complete and not force:
            return list(self._detected_plugins.values())

        self._detected_plugins = {}

        for slug, config in self.PLUGIN_ENDPOINTS.items():
            plugin = self._detect_plugin(slug, config)
            if plugin:
                self._detected_plugins[slug] = plugin

        self._detection_complete = True
        return list(self._detected_plugins.values())

    def get_plugin(self, slug: str) -> Optional[DetectedPlugin]:
        """Get a specific detected plugin by slug"""
        if not self._detection_complete:
            self.detect_all()
        return self._detected_plugins.get(slug)

    def get_redirect_handler(self) -> Optional[DetectedPlugin]:
        """
        Get the best available plugin for creating redirects.

        Returns the highest-priority plugin that supports redirects,
        or None if no capable plugin is installed.
        """
        if not self._detection_complete:
            self.detect_all()

        for slug in self.REDIRECT_PRIORITY:
            plugin = self._detected_plugins.get(slug)
            if plugin and plugin.can_create_redirects:
                return plugin

        return None

    def get_meta_handler(self) -> Optional[DetectedPlugin]:
        """
        Get the best available plugin for updating meta tags.

        Returns the highest-priority plugin that supports meta tags,
        or None if no capable plugin is installed.
        """
        if not self._detection_complete:
            self.detect_all()

        for slug in self.META_PRIORITY:
            plugin = self._detected_plugins.get(slug)
            if plugin and plugin.can_update_meta:
                return plugin

        return None

    def has_redirect_capability(self) -> bool:
        """Check if any installed plugin can create redirects"""
        return self.get_redirect_handler() is not None

    def has_meta_capability(self) -> bool:
        """Check if any installed plugin can update meta tags"""
        return self.get_meta_handler() is not None

    def get_detection_summary(self) -> Dict[str, Any]:
        """
        Get a summary of detected plugins and capabilities.

        Useful for displaying in the UI.
        """
        if not self._detection_complete:
            self.detect_all()

        plugins = list(self._detected_plugins.values())
        redirect_handler = self.get_redirect_handler()
        meta_handler = self.get_meta_handler()

        return {
            "plugins": [
                {
                    "name": p.name,
                    "slug": p.slug,
                    "is_premium": p.is_premium,
                    "can_redirects": p.can_create_redirects,
                    "can_meta": p.can_update_meta,
                }
                for p in plugins
            ],
            "capabilities": {
                "redirects": redirect_handler is not None,
                "redirects_handler": redirect_handler.name if redirect_handler else None,
                "meta_tags": meta_handler is not None,
                "meta_handler": meta_handler.name if meta_handler else None,
            },
            "recommendations": self._get_recommendations(),
        }

    def _get_recommendations(self) -> List[str]:
        """Get recommendations for missing capabilities"""
        recommendations = []

        if not self.has_redirect_capability():
            recommendations.append(
                "Install Rank Math or Redirection plugin to enable automatic redirects"
            )

        if not self.has_meta_capability():
            recommendations.append(
                "Install Rank Math or Yoast SEO to enable meta tag updates"
            )

        return recommendations
