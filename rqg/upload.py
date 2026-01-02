from pathlib import Path
import json
import os
from typing import Optional
import requests


def upload_bundle(bundle_path: str, api_url: Optional[str] = None, token: Optional[str] = None):
    api_url = api_url or os.getenv("RQG_API_URL")
    token = token or os.getenv("RQG_API_TOKEN")
    
    if not api_url:
        raise ValueError("API URL not provided. Set RQG_API_URL env var or use --api-url")
    
    bundle_file = Path(bundle_path)
    if not bundle_file.exists():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")
    
    with open(bundle_file, "r", encoding="utf-8") as f:
        bundle_data = json.load(f)
    
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    response = requests.post(
        f"{api_url}/api/v1/bundles",
        json=bundle_data,
        headers=headers,
    )
    
    response.raise_for_status()
    return response.json()

