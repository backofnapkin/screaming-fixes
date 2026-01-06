"""
WordPress SEO Plugin Integration Services.

This package provides unified interfaces for detecting and interacting with
popular WordPress SEO plugins like Rank Math, Yoast, and Redirection.
"""

from .plugin_detector import PluginDetector, DetectedPlugin, PluginCapability
from .seo_service import SEOService, NoCapablePluginError
from .rank_math import RankMathClient
from .redirection import RedirectionClient
from .yoast import YoastClient

__all__ = [
    'PluginDetector',
    'DetectedPlugin',
    'PluginCapability',
    'SEOService',
    'NoCapablePluginError',
    'RankMathClient',
    'RedirectionClient',
    'YoastClient',
]
