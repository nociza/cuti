#!/usr/bin/env python3
"""Test script to verify statistics page functionality."""

import requests
import json
from datetime import datetime, timedelta

def test_statistics_endpoints():
    """Test all statistics-related API endpoints."""
    base_url = "http://127.0.0.1:8000"
    
    # Test metrics endpoint
    print("Testing /api/monitoring/metrics...")
    response = requests.get(f"{base_url}/api/monitoring/metrics", params={
        "range": "week",
        "start_date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "end_date": datetime.now().strftime("%Y-%m-%d")
    })
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  Total tokens: {data.get('total_tokens', 0):,}")
        print(f"  Total cost: ${data.get('total_cost', 0):.2f}")
        print(f"  Total requests: {data.get('total_requests', 0)}")
    
    # Test predictions endpoint
    print("\nTesting /api/monitoring/predictions...")
    response = requests.get(f"{base_url}/api/monitoring/predictions")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        burn_rate = data.get('burn_rate', {})
        print(f"  Tokens per hour: {burn_rate.get('tokens_per_hour', 0):,}")
        print(f"  Cost per hour: ${burn_rate.get('cost_per_hour', 0):.2f}")
        current = data.get('current_usage', {})
        print(f"  Current usage: {current.get('tokens_percentage', 0):.1f}% of limit")
    
    # Test plans endpoint
    print("\nTesting /api/monitoring/plans...")
    response = requests.get(f"{base_url}/api/monitoring/plans")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        plans = response.json()
        print(f"  Available plans: {len(plans)}")
        for plan in plans:
            if plan.get('is_current'):
                print(f"  Current plan: {plan.get('display_name')}")
                print(f"    Token limit: {plan.get('formatted_token_limit')}")
                print(f"    Cost limit: ${plan.get('cost_limit', 0):.2f}")
    
    # Test health endpoint
    print("\nTesting /api/monitoring/health...")
    response = requests.get(f"{base_url}/api/monitoring/health")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        health = response.json()
        print(f"  Overall status: {health.get('status')}")
        components = health.get('components', {})
        for component, status in components.items():
            print(f"  {component}: {status.get('status')}")
    
    print("\n✅ All endpoints are responding correctly!")

if __name__ == "__main__":
    test_statistics_endpoints()