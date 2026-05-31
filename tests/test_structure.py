"""
Smoke tests that verify the project structure and that the obsolete
queue / multi-agent subsystems have been fully removed.
"""

import sys
from pathlib import Path


def test_project_structure():
    """Key directories and packaging metadata exist."""
    project_root = Path(__file__).parent.parent

    assert (project_root / "src" / "cuti").exists(), "Source package should exist"
    assert (project_root / "tests").exists(), "Tests directory should exist"
    assert (project_root / "pyproject.toml").exists(), "pyproject.toml should exist"


def test_obsolete_subsystems_removed():
    """The queue, multi-agent, todo, and alias subsystems are gone."""
    pkg = Path(__file__).parent.parent / "src" / "cuti"

    removed = [
        "agents",
        "core/queue.py",
        "core/storage.py",
        "core/models.py",
        "services/queue_service.py",
        "services/task_expansion.py",
        "services/aliases.py",
        "services/todo_service.py",
        "cli/commands/queue.py",
        "cli/commands/agent.py",
        "cli/commands/todo.py",
        "cli/commands/alias.py",
        "models.py",
        "queue_manager.py",
    ]
    present = [rel for rel in removed if (pkg / rel).exists()]
    assert not present, f"obsolete modules should be removed: {present}"


def test_package_imports():
    """The package and CLI import cleanly."""
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "src"))

    import cuti  # noqa: F401
    import cuti.cli.app  # noqa: F401

    assert isinstance(cuti.__version__, str)


if __name__ == "__main__":
    test_project_structure()
    test_obsolete_subsystems_removed()
    test_package_imports()
    print("All structure tests passed!")
