"""Load versioned prompt files and inject shared context variables.

Usage:
    from services.prompt_loader import load_prompt, load_context

    ctx = load_context()
    prompt = load_prompt("school_discovery_prompt_v1", context=ctx)
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_context() -> Dict[str, Any]:
    """Load the shared common_context.json policy file."""
    path = _PROMPTS_DIR / "common_context.json"
    if not path.exists():
        logger.warning("common_context.json not found at %s", path)
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_prompt(
    name: str,
    *,
    context: Optional[Dict[str, Any]] = None,
    extra_vars: Optional[Dict[str, Any]] = None,
) -> str:
    """Load a prompt .md file by name and substitute template variables.

    Template variables use the ``{{variable_name}}`` syntax.
    Values are first looked up in *extra_vars*, then in *context*.

    Args:
        name: Prompt file name without extension (e.g. "school_discovery_prompt_v1").
        context: Shared context dict (from load_context). Loaded automatically if None.
        extra_vars: Additional variables to substitute beyond the shared context.

    Returns:
        The prompt text with variables replaced.
    """
    path = _PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        template = f.read()

    if context is None:
        context = load_context()

    # Merge context + extra_vars (extra takes precedence)
    variables: Dict[str, Any] = {**context}
    if extra_vars:
        variables.update(extra_vars)

    def _replace(match: re.Match) -> str:
        key = match.group(1).strip()
        if key in variables:
            val = variables[key]
            # Serialize non-string values as JSON
            if isinstance(val, (list, dict)):
                return json.dumps(val)
            return str(val)
        logger.debug("Template variable not found: {{%s}}", key)
        return match.group(0)  # leave unreplaced

    result = re.sub(r"\{\{(.+?)\}\}", _replace, template)
    return result


def list_prompts() -> list[str]:
    """Return available prompt file names (without extension)."""
    if not _PROMPTS_DIR.exists():
        return []
    return sorted(p.stem for p in _PROMPTS_DIR.glob("*.md"))
