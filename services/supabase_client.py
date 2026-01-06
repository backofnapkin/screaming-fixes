"""
Supabase client for storing leads and scan results
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List
import requests

from config import get_secret


class SupabaseClient:
    """Client for interacting with Supabase database"""

    def __init__(self):
        # Fetch credentials dynamically (important for Streamlit Cloud where
        # st.secrets may not be available at module import time)
        self.url = get_secret("SUPABASE_URL", "https://yybfjsjysfteqjvicuuy.supabase.co")
        self.key = get_secret("SUPABASE_KEY", "")
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make a request to Supabase REST API"""
        url = f"{self.url}/rest/v1/{endpoint}"

        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=data)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "PATCH":
                response = requests.patch(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json() if response.text else {}
        except requests.exceptions.RequestException as e:
            print(f"Supabase request error: {e}")
            return {}

    def create_lead(
        self,
        email: str,
        domain: str,
        broken_backlinks_count: int,
        top_referrers: List[Dict],
        ip_address: Optional[str] = None,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        source: str = "backlink_reclaim"
    ) -> Optional[Dict]:
        """
        Create a new lead in the database

        Returns the created lead record or None on failure
        """
        data = {
            "email": email,
            "domain": domain,
            "source": source,
            "broken_backlinks_count": broken_backlinks_count,
            "top_referrers": top_referrers,
            "ip_address": ip_address,
            "utm_source": utm_source,
            "utm_medium": utm_medium,
            "utm_campaign": utm_campaign,
            "email_verified": False
        }

        result = self._request("POST", "leads", data)

        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return None

    def create_scan(
        self,
        domain: str,
        broken_backlinks_count: int,
        total_backlinks: int,
        results_json: List[Dict],
        ip_address: Optional[str] = None,
        lead_id: Optional[str] = None,
        api_cost_cents: int = 0
    ) -> Optional[Dict]:
        """
        Create a new scan record in the database

        Returns the created scan record or None on failure
        """
        data = {
            "domain": domain,
            "broken_backlinks_count": broken_backlinks_count,
            "total_backlinks": total_backlinks,
            "results_json": results_json,
            "ip_address": ip_address,
            "lead_id": lead_id,
            "api_cost_cents": api_cost_cents
        }

        result = self._request("POST", "scans", data)

        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return None

    def get_lead_by_email(self, email: str) -> Optional[Dict]:
        """Get a lead by email address"""
        url = f"{self.url}/rest/v1/leads?email=eq.{email}&limit=1"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            if result and len(result) > 0:
                return result[0]
        except requests.exceptions.RequestException:
            pass

        return None

    def get_scans_by_domain(self, domain: str, limit: int = 10) -> List[Dict]:
        """Get recent scans for a domain"""
        url = f"{self.url}/rest/v1/scans?domain=eq.{domain}&order=created_at.desc&limit={limit}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return []

    def update_lead(self, lead_id: str, updates: Dict) -> bool:
        """Update a lead record"""
        url = f"{self.url}/rest/v1/leads?id=eq.{lead_id}"

        try:
            response = requests.patch(url, headers=self.headers, json=updates)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False
