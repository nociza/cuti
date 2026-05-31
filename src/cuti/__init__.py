"""cuti — an instant, containerized Claude Code dev environment.

Launch a ready-to-use Claude Code workspace in Docker with ``cuti container``,
manage agent-CLI providers and Claude accounts, and inspect usage and history.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("cuti")
except PackageNotFoundError:  # pragma: no cover - source checkout without install
    __version__ = "0.0.0"

__author__ = "claude-code, nociza"
__description__ = (
    "An instant, containerized Claude Code dev environment with provider, "
    "account, history, and usage tooling."
)

__all__ = ["__version__", "__author__", "__description__"]
