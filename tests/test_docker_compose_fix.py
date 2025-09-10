#!/usr/bin/env python3
"""
Test script to verify docker-compose works in subprocess calls.
This simulates what the authentified-core dev.py script does.
"""

import subprocess
import sys

def check_docker_installed():
    """Check if docker-compose is installed and accessible."""
    try:
        # Test 1: Direct command (what was failing)
        print("Test 1: Running docker-compose --version directly...")
        result = subprocess.run(
            ["docker-compose", "--version"], 
            capture_output=True, 
            check=True,
            text=True
        )
        print(f"✅ Success: {result.stdout.strip()}")
        return "docker-compose"
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed with CalledProcessError: {e}")
        print(f"   stdout: {e.stdout}")
        print(f"   stderr: {e.stderr}")
    except PermissionError as e:
        print(f"❌ Failed with PermissionError: {e}")
    except FileNotFoundError as e:
        print(f"❌ Failed with FileNotFoundError: {e}")
    
    # Test 2: Try with shell=True
    print("\nTest 2: Running with shell=True...")
    try:
        result = subprocess.run(
            "docker-compose --version", 
            shell=True,
            capture_output=True, 
            check=True,
            text=True
        )
        print(f"✅ Success with shell: {result.stdout.strip()}")
        return "docker-compose"
    except Exception as e:
        print(f"❌ Failed with shell: {e}")
    
    # Test 3: Try docker compose directly
    print("\nTest 3: Running docker compose version...")
    try:
        result = subprocess.run(
            ["docker", "compose", "version"], 
            capture_output=True, 
            check=True,
            text=True
        )
        print(f"✅ Success with docker compose: {result.stdout.strip()}")
        return "docker compose"
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    return None

def test_docker_compose_up():
    """Test running docker-compose up command."""
    print("\nTest 4: Simulating docker-compose up --help...")
    try:
        result = subprocess.run(
            ["docker-compose", "up", "--help"],
            capture_output=True,
            check=True,
            text=True
        )
        print("✅ docker-compose up --help works!")
        print(f"   Output lines: {len(result.stdout.splitlines())}")
    except Exception as e:
        print(f"❌ docker-compose up failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Docker Compose Subprocess Test")
    print("=" * 60)
    
    compose_cmd = check_docker_installed()
    
    if compose_cmd:
        print(f"\n✅ Docker Compose is accessible via: {compose_cmd}")
        test_docker_compose_up()
    else:
        print("\n❌ Docker Compose is NOT accessible via subprocess")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)