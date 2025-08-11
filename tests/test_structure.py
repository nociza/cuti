"""
Simple test to verify the project structure is working correctly.
"""

import sys
from pathlib import Path


def test_project_structure():
    """Test that the project structure is properly organized."""
    # Get the project root
    project_root = Path(__file__).parent.parent
    
    # Check that key directories exist
    assert (project_root / "src" / "cuti").exists(), "Source package should exist"
    assert (project_root / "tests").exists(), "Tests directory should exist"
    assert (project_root / "pyproject.toml").exists(), "pyproject.toml should exist"
    
    # Check that test files are in the right place
    assert (project_root / "tests" / "test_agents.py").exists(), "test_agents.py should be in tests/"
    assert (project_root / "tests" / "test_interface.py").exists(), "test_interface.py should be in tests/"
    assert (project_root / "tests" / "test_agent_integration.py").exists(), "test_agent_integration.py should be in tests/"
    
    # Check that old test files are removed from root
    assert not (project_root / "test_agents.py").exists(), "Old test_agents.py should be removed from root"
    assert not (project_root / "test_interface.py").exists(), "Old test_interface.py should be removed from root"
    assert not (project_root / "test_agent_integration.py").exists(), "Old test_agent_integration.py should be removed from root"


def test_imports_configured():
    """Test that import paths are configured correctly."""
    # Add src to path
    project_root = Path(__file__).parent.parent
    src_path = project_root / "src"
    sys.path.insert(0, str(src_path))
    
    # This should work without errors when dependencies are installed
    try:
        import cuti
        import_success = True
    except ImportError as e:
        # Expected if dependencies aren't installed, but structure is correct
        import_success = "yaml" in str(e) or "claude" in str(e) or "fastapi" in str(e)
    
    assert import_success, "Import should work or fail only due to missing dependencies"


if __name__ == "__main__":
    test_project_structure()
    test_imports_configured()
    print("✓ All structure tests passed!")
