"""Shared Jupyter bootstrap: locate ``deploy/``, ``chdir`` there, and prepend ``sys.path``."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def activate() -> Path:
    """Return the ``deploy/`` directory and make it the working directory for imports."""
    cwd = Path.cwd().resolve()
    if (cwd / "utils.py").is_file():
        deploy_dir = cwd
    elif (cwd / "deploy" / "utils.py").is_file():
        deploy_dir = (cwd / "deploy").resolve()
    else:
        raise FileNotFoundError(
            "Could not find deploy/utils.py. Start Jupyter from the repository root "
            "(parent of deploy/) or from inside deploy/."
        )
    os.chdir(deploy_dir)
    s = str(deploy_dir)
    if s not in sys.path:
        sys.path.insert(0, s)
    return deploy_dir
