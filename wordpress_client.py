"""
WordPress REST API Client

Handles authentication and content updates for WordPress.
Uses Application Passwords for secure authentication.
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, quote

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


@dataclass
class WordPressCredentials:
    """WordPress connection credentials"""
    site_url: str
    username: str
    password: str  # Application Password
    
    @property
    def api_base(self) -> str:
        """Get the REST API base URL"""
        url = self.site_url.rstrip('/')
        return f"{url}/wp-json/wp/v2"
    
    @property
    def auth(self) -> tuple:
        """Get auth tuple for requests"""
        # Application passwords may have spaces
        clean_password = self.password.replace(' ', '')
        return (self.username, clean_password)


class WordPressClient:
    """
    WordPress REST API client for fixing broken links.
    
    Usage:
        client = WordPressClient(
            site_url="https://example.com",
            username="admin",
            password="xxxx xxxx xxxx xxxx"
        )
        
        # Test connection
        if client.test_connection()['success']:
            # Find post by URL
            post_id = client.find_post_id_by_url("https://example.com/my-post/")
            
            # Remove a broken link
            client.remove_link(post_id, "https://broken-link.com/page")
    """
    
    def __init__(
        self,
        site_url: str,
        username: str,
        password: str,
        timeout: int = 30
    ):
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx is required. Install with: pip install httpx")
        
        self.credentials = WordPressCredentials(
            site_url=site_url,
            username=username,
            password=password
        )
        self.timeout = timeout
        self._client = None
    
    @property
    def client(self) -> "httpx.Client":
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.Client(
                auth=self.credentials.auth,
                timeout=self.timeout,
                follow_redirects=True
            )
        return self._client
    
    def close(self):
        """Close the HTTP client"""
        if self._client:
            self._client.close()
            self._client = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
    
    # =========================================================================
    # Connection Testing
    # =========================================================================
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the WordPress connection"""
        try:
            url = f"{self.credentials.api_base}/users/me"
            response = self.client.get(url)
            
            if response.status_code == 200:
                user = response.json()
                return {
                    "success": True,
                    "message": f"Connected as {user.get('name', user.get('slug'))}",
                    "user": user
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": "Authentication failed. Check username and application password."
                }
            else:
                return {
                    "success": False,
                    "message": f"Connection failed: HTTP {response.status_code}"
                }
                
        except httpx.ConnectError:
            return {
                "success": False,
                "message": f"Could not connect to {self.credentials.site_url}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection error: {str(e)}"
            }
    
    # =========================================================================
    # Post ID Discovery
    # =========================================================================
    
    def find_post_id_by_url(self, page_url: str) -> Optional[int]:
        """
        Find a post/page ID by its URL.
        
        Tries multiple methods:
        1. Search by slug
        2. Check for shortlink in page HTML
        3. Query by link (requires pretty permalinks)
        """
        # Method 1: Extract slug and search
        parsed = urlparse(page_url)
        path = parsed.path.strip('/')
        slug = path.split('/')[-1] if path else None
        
        if slug:
            # Try posts
            post_id = self._find_by_slug(slug, 'posts')
            if post_id:
                return post_id
            
            # Try pages
            post_id = self._find_by_slug(slug, 'pages')
            if post_id:
                return post_id
        
        # Method 2: Fetch page and look for shortlink
        try:
            response = self.client.get(page_url)
            if response.status_code == 200:
                # Look for shortlink: <link rel='shortlink' href='...?p=123' />
                match = re.search(r"rel=['\"]shortlink['\"][^>]+href=['\"][^'\"]*\?p=(\d+)", response.text)
                if match:
                    return int(match.group(1))
                
                # Look for post ID in body class: postid-123
                match = re.search(r'postid-(\d+)', response.text)
                if match:
                    return int(match.group(1))
                
                # Look for page ID in body class: page-id-123
                match = re.search(r'page-id-(\d+)', response.text)
                if match:
                    return int(match.group(1))
        except:
            pass
        
        return None
    
    def _find_by_slug(self, slug: str, post_type: str = 'posts') -> Optional[int]:
        """Find post ID by slug"""
        try:
            url = f"{self.credentials.api_base}/{post_type}"
            params = {"slug": slug, "status": "any"}
            
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                results = response.json()
                if results:
                    return results[0]['id']
        except:
            pass
        return None
    
    # =========================================================================
    # Content Retrieval
    # =========================================================================
    
    def get_post(self, post_id: int) -> Optional[Dict]:
        """Get a post by ID"""
        try:
            url = f"{self.credentials.api_base}/posts/{post_id}"
            params = {"context": "edit"}
            
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            
            # Try pages
            url = f"{self.credentials.api_base}/pages/{post_id}"
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                return response.json()
                
        except:
            pass
        return None
    
    def get_post_content(self, post_id: int) -> Optional[str]:
        """Get raw post content"""
        post = self.get_post(post_id)
        if post:
            content = post.get('content', {})
            if isinstance(content, dict):
                return content.get('raw', content.get('rendered', ''))
            return str(content)
        return None
    
    # =========================================================================
    # Link Fixing
    # =========================================================================
    
    def remove_link(
        self,
        post_id: int,
        broken_url: str,
        keep_anchor_text: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Remove a broken link from a post, keeping the anchor text.
        
        Args:
            post_id: The post ID
            broken_url: URL to remove
            keep_anchor_text: If True, keep the text; if False, remove entirely
            dry_run: If True, don't actually update
        
        Returns:
            Dict with success, message, and details
        """
        try:
            content = self.get_post_content(post_id)
            if not content:
                return {"success": False, "message": "Could not retrieve post content"}
            
            # Escape URL for regex
            escaped_url = re.escape(broken_url)
            
            # Pattern to match the link
            if keep_anchor_text:
                # Replace <a href="url">text</a> with just text
                pattern = rf'<a[^>]*href=["\']?{escaped_url}["\']?[^>]*>(.*?)</a>'
                replacement = r'\1'
            else:
                # Remove entire link including text
                pattern = rf'<a[^>]*href=["\']?{escaped_url}["\']?[^>]*>.*?</a>'
                replacement = ''
            
            # Count matches
            matches = re.findall(pattern, content, flags=re.IGNORECASE | re.DOTALL)
            
            if not matches:
                return {
                    "success": False,
                    "message": "Link not found in content",
                    "matches": 0
                }
            
            # Make replacement
            new_content = re.sub(pattern, replacement, content, flags=re.IGNORECASE | re.DOTALL)
            
            if not dry_run:
                # Update the post
                self._update_post_content(post_id, new_content)
            
            return {
                "success": True,
                "message": f"{'Would remove' if dry_run else 'Removed'} {len(matches)} link(s)",
                "matches": len(matches),
                "dry_run": dry_run
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def replace_link(
        self,
        post_id: int,
        old_url: str,
        new_url: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Replace a URL in a post's content.
        
        Args:
            post_id: The post ID
            old_url: URL to find and replace
            new_url: Replacement URL
            dry_run: If True, don't actually update
        
        Returns:
            Dict with success, message, and details
        """
        try:
            content = self.get_post_content(post_id)
            if not content:
                return {"success": False, "message": "Could not retrieve post content"}
            
            # Count occurrences
            count = content.count(old_url)
            
            if count == 0:
                return {
                    "success": False,
                    "message": "URL not found in content",
                    "replacements": 0
                }
            
            # Make replacement
            new_content = content.replace(old_url, new_url)
            
            if not dry_run:
                self._update_post_content(post_id, new_content)
            
            return {
                "success": True,
                "message": f"{'Would replace' if dry_run else 'Replaced'} {count} occurrence(s)",
                "replacements": count,
                "dry_run": dry_run
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def _update_post_content(self, post_id: int, new_content: str) -> bool:
        """Update post content via API"""
        # Try posts endpoint first
        url = f"{self.credentials.api_base}/posts/{post_id}"
        response = self.client.post(url, json={"content": new_content})
        
        if response.status_code == 200:
            return True
        
        # Try pages endpoint
        url = f"{self.credentials.api_base}/pages/{post_id}"
        response = self.client.post(url, json={"content": new_content})
        
        return response.status_code == 200
    
    # =========================================================================
    # Batch Operations
    # =========================================================================
    
    def update_alt_text(
        self,
        post_id: int,
        img_src: str,
        new_alt: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Update alt text for an image in a post's content.
        
        Args:
            post_id: The post ID
            img_src: Image src URL to find
            new_alt: New alt text to set
            dry_run: If True, don't actually update
        
        Returns:
            Dict with success, message, and details
        """
        try:
            content = self.get_post_content(post_id)
            if not content:
                return {"success": False, "message": "Could not retrieve post content"}
            
            # Escape special regex characters in img_src
            escaped_src = re.escape(img_src)
            
            # Count how many times this image appears
            # Match img tags with this src (handles both src="url" and src='url')
            img_pattern = rf'<img[^>]*src=["\']?{escaped_src}["\']?[^>]*>'
            matches = re.findall(img_pattern, content, flags=re.IGNORECASE)
            
            if not matches:
                return {
                    "success": False,
                    "message": "Image not found in content",
                    "updates": 0
                }
            
            # Escape the new alt text for safe insertion (escape quotes)
            safe_new_alt = new_alt.replace('"', '&quot;').replace("'", '&#39;')
            
            # Function to update alt in a single img tag
            def update_img_alt(match):
                img_tag = match.group(0)
                
                # Check if alt attribute exists
                if re.search(r'\salt=["\'][^"\']*["\']', img_tag, re.IGNORECASE):
                    # Replace existing alt attribute
                    updated = re.sub(
                        r'(\salt=)["\'][^"\']*["\']',
                        f'\\1"{safe_new_alt}"',
                        img_tag,
                        flags=re.IGNORECASE
                    )
                elif re.search(r'\salt=\S+', img_tag, re.IGNORECASE):
                    # Handle alt without quotes (alt=something)
                    updated = re.sub(
                        r'(\salt=)\S+',
                        f'\\1"{safe_new_alt}"',
                        img_tag,
                        flags=re.IGNORECASE
                    )
                else:
                    # No alt attribute - add one after src
                    updated = re.sub(
                        rf'(src=["\']?{escaped_src}["\']?)',
                        f'\\1 alt="{safe_new_alt}"',
                        img_tag,
                        flags=re.IGNORECASE
                    )
                
                return updated
            
            # Apply updates to all matching img tags
            new_content = re.sub(img_pattern, update_img_alt, content, flags=re.IGNORECASE)
            
            if new_content == content:
                return {
                    "success": False,
                    "message": "No changes made (alt text may already be set)",
                    "updates": 0
                }
            
            if not dry_run:
                self._update_post_content(post_id, new_content)
            
            return {
                "success": True,
                "message": f"{'Would update' if dry_run else 'Updated'} {len(matches)} image(s)",
                "updates": len(matches),
                "dry_run": dry_run
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    # =========================================================================
    # Batch Operations
    # =========================================================================
    
    def batch_find_post_ids(self, urls: List[str]) -> Dict[str, Optional[int]]:
        """
        Find post IDs for multiple URLs.
        
        Returns:
            Dict mapping URL to post ID (or None if not found)
        """
        results = {}
        for url in urls:
            results[url] = self.find_post_id_by_url(url)
        return results
    
    def batch_remove_links(
        self,
        fixes: List[Dict],
        dry_run: bool = False
    ) -> List[Dict]:
        """
        Remove multiple broken links.
        
        Args:
            fixes: List of dicts with 'post_id' and 'broken_url'
            dry_run: If True, don't actually update
        
        Returns:
            List of result dicts
        """
        results = []
        for fix in fixes:
            result = self.remove_link(
                post_id=fix['post_id'],
                broken_url=fix['broken_url'],
                dry_run=dry_run
            )
            result['source_url'] = fix.get('source_url', '')
            result['broken_url'] = fix['broken_url']
            results.append(result)
        return results


# =============================================================================
# Convenience Functions
# =============================================================================

def test_wordpress_connection(
    site_url: str,
    username: str,
    password: str
) -> Dict[str, Any]:
    """Test WordPress connection without creating persistent client"""
    try:
        with WordPressClient(site_url, username, password) as client:
            return client.test_connection()
    except ImportError as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}
