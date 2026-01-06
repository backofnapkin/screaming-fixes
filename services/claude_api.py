"""
Claude API service for Screaming Fixes.
Handles all AI-powered suggestions for broken links and image alt text.
"""

import os
import re
import json
from typing import Dict, Optional, Callable

from config import AGENT_MODE_API_KEY, LANGSMITH_ENABLED

# Optional imports
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# LangSmith tracking (optional)
try:
    from langsmith import Client as LangSmithClient
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False


def track_event(event_name: str, metadata: Dict = None):
    """Track an analytics event to LangSmith (silent, non-blocking)"""
    if not LANGSMITH_ENABLED or not LANGSMITH_AVAILABLE:
        return

    try:
        client = LangSmithClient()
        client.create_run(
            name=event_name,
            run_type="chain",
            inputs=metadata or {},
            project_name=os.environ.get("LANGCHAIN_PROJECT", "screaming-fixes"),
        )
    except Exception:
        pass  # Silent fail - don't interrupt user experience


def get_ai_suggestion(broken_url: str, info: Dict, domain: str, api_key: str) -> Dict[str, str]:
    """Get AI suggestion for a single broken URL with web search"""

    # Track AI suggestion request (no URLs/PII)
    is_agent_mode_key = api_key == AGENT_MODE_API_KEY
    track_event("ai_suggestion_request", {
        "is_agent_mode_key": is_agent_mode_key,
        "is_internal": info['is_internal'],
        "status_code": info['status_code'],
        "affected_pages": info['count']
    })

    if not ANTHROPIC_AVAILABLE:
        return {'action': 'remove', 'url': None, 'notes': 'Anthropic library not installed.'}

    try:
        client = Anthropic(api_key=api_key)

        anchors_text = ', '.join(f'"{a}"' for a in info['anchors'][:5])
        if len(info['anchors']) > 5:
            anchors_text += f' (+{len(info["anchors"]) - 5} more)'

        type_label = "internal" if info['is_internal'] else "external"

        prompt = f"""You are helping fix broken links on {domain}.

BROKEN URL: {broken_url}
STATUS: {info['status_code']} {info['status_text']}
TYPE: {type_label}
ANCHOR TEXTS USED: {anchors_text}
APPEARS ON: {info['count']} page(s)

Your task:
1. If INTERNAL, search {domain} to find if similar content exists at a different URL
2. If EXTERNAL, check if the content has moved to a new URL
3. Recommend REMOVE (delete link, keep anchor text) or REPLACE (with specific URL)

IMPORTANT:
- Only suggest REPLACE if you find a real working URL
- Default to REMOVE if no good replacement exists
- Keep notes to 1-2 sentences

Respond in JSON format:
{{"action": "remove" or "replace", "url": "replacement URL or null", "notes": "brief explanation"}}

Only output the JSON."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 3
            }],
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                result_text += block.text

        try:
            json_match = re.search(r'\{[^}]+\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    'action': result.get('action', 'remove'),
                    'url': result.get('url'),
                    'notes': result.get('notes', 'No explanation provided.')
                }
        except json.JSONDecodeError:
            pass

        return {'action': 'remove', 'url': None, 'notes': result_text[:150] if result_text else 'Could not parse response.'}

    except Exception as e:
        return {'action': 'remove', 'url': None, 'notes': f'Error: {str(e)[:100]}'}


def get_ai_alt_text_suggestion(image_url: str, info: Dict, domain: str, api_key: str) -> Dict[str, str]:
    """Get AI suggestion for image alt text using Claude's vision capability"""

    # Track AI suggestion request (no URLs/PII)
    is_agent_mode_key = api_key == AGENT_MODE_API_KEY
    track_event("ai_alt_text_request", {
        "is_agent_mode_key": is_agent_mode_key,
        "alt_status": info['alt_status'],
        "affected_pages": info['count']
    })

    if not ANTHROPIC_AVAILABLE:
        return {'alt_text': '', 'notes': 'Anthropic library not installed.'}

    try:
        client = Anthropic(api_key=api_key)

        # Get context from source pages
        source_urls = info['sources'][:3]  # First 3 source pages for context
        source_context = '\n'.join(f"- {url}" for url in source_urls)

        current_alt = info['current_alt'] if info['current_alt'] else '(empty)'

        prompt = f"""You are helping optimize image alt text for SEO on {domain}.

IMAGE URL: {image_url}
CURRENT ALT TEXT: {current_alt}
ISSUE: {info['alt_status']} (needs descriptive alt text)
APPEARS ON PAGES:
{source_context}

Your task:
1. Look at the image
2. Consider the context from the page URLs where it appears
3. Write descriptive, SEO-friendly alt text

Alt text best practices:
- Be descriptive but concise (10-125 characters ideal)
- Describe what's actually IN the image
- Include relevant keywords naturally
- Don't start with "Image of" or "Picture of" (screen readers already announce it's an image)
- Consider the page context for relevance

Respond in JSON format:
{{"alt_text": "your suggested alt text", "notes": "brief explanation of what you see in the image"}}

Only output the JSON."""

        # Try to include the image for vision analysis
        messages = []

        # Check if image URL is accessible (basic check)
        if image_url.startswith('http'):
            messages = [{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "url",
                            "url": image_url
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        else:
            # Fallback to text-only if image URL is relative/invalid
            messages = [{"role": "user", "content": prompt}]

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=messages
        )

        result_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                result_text += block.text

        try:
            json_match = re.search(r'\{[^}]+\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    'alt_text': result.get('alt_text', ''),
                    'notes': result.get('notes', 'No explanation provided.')
                }
        except json.JSONDecodeError:
            pass

        return {'alt_text': '', 'notes': result_text[:150] if result_text else 'Could not parse response.'}

    except Exception as e:
        error_msg = str(e)
        # Provide helpful message for common image loading errors
        if 'Could not process image' in error_msg or 'invalid_request_error' in error_msg:
            return {'alt_text': '', 'notes': 'Could not load image. The image may be inaccessible, blocked, or in an unsupported format. Try entering alt text manually.'}
        return {'alt_text': '', 'notes': f'Error: {error_msg[:100]}'}


def is_anthropic_available() -> bool:
    """Check if Anthropic library is available"""
    return ANTHROPIC_AVAILABLE
