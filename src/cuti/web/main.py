"""Compatibility entry point for the cuti ops console."""

from .app import create_app, main

__all__ = ["create_app", "main"]


if __name__ == "__main__":
    main()
