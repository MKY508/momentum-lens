"""Commands package: split interactive menus into focused modules.
Each command module exposes a run(state) -> new_state or None API.
"""
from .about import show_about

__all__ = ["show_about"]
