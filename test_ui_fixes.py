#!/usr/bin/env python3
"""
Test script to verify UI fixes in the cuti web interface.
Run the web server first: python run.py web
Then open a browser to test the following:

1. Task Tracker Toggle Button z-index fix
   - Navigate to http://localhost:8001
   - Verify the task tracker toggle button (clipboard icon) is visible and clickable
   - It should appear above the navigation bar

2. Workspace Path Display
   - Check the header workspace display
   - Should show only the folder name by default (e.g., "cuti")
   - On hover, should expand to show full path

3. Tab Navigation Animation Removal
   - Click between Terminal, History, and Settings tabs
   - Transitions should be instant with no animation

4. Statistics Page
   - Navigate to http://localhost:8001/statistics
   - Should see comprehensive usage metrics
   - Charts should be visible and interactive
   - Export buttons should be functional
"""

import sys
import time
from pathlib import Path
import urllib.request
import urllib.error

def test_endpoints():
    """Test that all endpoints are accessible."""
    base_url = "http://localhost:8000"
    
    endpoints = [
        "/",           # Chat page
        "/agents",     # Agent Manager
        "/statistics", # New Statistics page
    ]
    
    print("Testing endpoints...")
    all_ok = True
    
    for endpoint in endpoints:
        try:
            with urllib.request.urlopen(f"{base_url}{endpoint}", timeout=5) as response:
                if response.status == 200:
                    print(f"✅ {endpoint} - OK")
                else:
                    print(f"❌ {endpoint} - Status {response.status}")
                    all_ok = False
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"❌ {endpoint} - Error: {e}")
            all_ok = False
    
    return all_ok

def check_css_changes():
    """Verify CSS changes were applied."""
    css_file = Path(__file__).parent / "src" / "cuti" / "web" / "static" / "css" / "main.css"
    
    if not css_file.exists():
        print("❌ CSS file not found")
        return False
    
    content = css_file.read_text()
    
    checks = [
        ("z-index: 110", "Task tracker z-index fix"),
        ("transition: none; /* Removed animation", "Animation removal"),
        (".working-dir-full", "Workspace path hover styles"),
    ]
    
    print("\nChecking CSS modifications...")
    all_ok = True
    
    for check_str, description in checks:
        if check_str in content:
            print(f"✅ {description}")
        else:
            print(f"❌ {description} - not found")
            all_ok = False
    
    return all_ok

def check_templates():
    """Verify template changes."""
    templates_dir = Path(__file__).parent / "src" / "cuti" / "web" / "templates"
    
    # Check statistics.html exists
    stats_template = templates_dir / "statistics.html"
    if stats_template.exists():
        print("\n✅ Statistics template created")
        # Check for key components
        content = stats_template.read_text()
        if "Chart.js" in content and "statisticsInterface" in content:
            print("✅ Statistics page has required components")
        else:
            print("❌ Statistics page missing components")
    else:
        print("\n❌ Statistics template not found")
        return False
    
    # Check header.html modifications
    header_template = templates_dir / "components" / "header.html"
    if header_template.exists():
        content = header_template.read_text()
        if "showFullPath" in content:
            print("✅ Header workspace path hover functionality added")
        else:
            print("❌ Header workspace path hover not implemented")
    
    return True

def main():
    print("=" * 60)
    print("cuti Web Interface UI Fixes Test")
    print("=" * 60)
    
    print("\n⚠️  Make sure the web server is running:")
    print("    python run.py web")
    print("\nTesting in 3 seconds...")
    time.sleep(3)
    
    # Run tests
    endpoints_ok = test_endpoints()
    css_ok = check_css_changes()
    templates_ok = check_templates()
    
    print("\n" + "=" * 60)
    if endpoints_ok and css_ok and templates_ok:
        print("✅ All tests passed!")
        print("\nManual verification needed:")
        print("1. Open http://localhost:8000 in your browser")
        print("2. Check task tracker toggle button is above navbar")
        print("3. Hover over workspace path to see full path")
        print("4. Switch tabs to verify instant transitions")
        print("5. Navigate to Statistics page and test features")
    else:
        print("❌ Some tests failed. Please review the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()