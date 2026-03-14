"""Gemini 1.5 Flash integration for digest summarization."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from config import get_settings

logger = logging.getLogger(__name__)

# Approximate pricing per 1M tokens (Gemini 1.5 Flash as of 2024)
GEMINI_FLASH_INPUT_COST_PER_1M = 0.075
GEMINI_FLASH_OUTPUT_COST_PER_1M = 0.30


@dataclass
class LLMResult:
    """Result from an LLM call with usage metadata."""

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost based on model and token counts."""
    if "flash" in model.lower():
        return (
            prompt_tokens * GEMINI_FLASH_INPUT_COST_PER_1M / 1_000_000
            + completion_tokens * GEMINI_FLASH_OUTPUT_COST_PER_1M / 1_000_000
        )
    if "gpt-4o-mini" in model.lower():
        return (
            prompt_tokens * 0.15 / 1_000_000
            + completion_tokens * 0.60 / 1_000_000
        )
    return 0.0


def generate(
    prompt: str,
    system_instruction: Optional[str] = None,
) -> LLMResult:
    """Generate text using Gemini 1.5 Flash.

    Falls back to OpenAI GPT-4o-mini if Gemini key is not set.
    Falls back to empty result if neither key is available.
    """
    settings = get_settings()

    if settings.gemini_api_key:
        try:
            return _gemini_generate(prompt, system_instruction, settings)
        except Exception as exc:
            logger.warning("Gemini generation failed, trying OpenAI fallback: %s", exc)

    if settings.openai_api_key:
        try:
            return _openai_generate(prompt, system_instruction, settings)
        except Exception as exc:
            logger.warning("OpenAI generation failed: %s", exc)

    return LLMResult(text="", model="none", prompt_tokens=0, completion_tokens=0)


def _gemini_generate(
    prompt: str,
    system_instruction: Optional[str],
    settings: Any,
) -> LLMResult:
    """Call Google Generative AI (Gemini) API."""
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model_name = settings.gemini_model

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_instruction,
    )

    response = model.generate_content(prompt)

    text = response.text or ""
    prompt_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
    completion_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0

    cost = _estimate_cost(model_name, prompt_tokens, completion_tokens)

    logger.info(
        "Gemini generation: model=%s, prompt_tokens=%d, completion_tokens=%d, cost=$%.6f",
        model_name, prompt_tokens, completion_tokens, cost,
    )

    return LLMResult(
        text=text,
        model=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost_usd=cost,
    )


def _openai_generate(
    prompt: str,
    system_instruction: Optional[str],
    settings: Any,
) -> LLMResult:
    """Fallback: call OpenAI Chat Completions API."""
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    model_name = settings.openai_model

    messages: List[Dict[str, str]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.4,
        max_tokens=1024,
    )

    text = response.choices[0].message.content or ""
    prompt_tokens = response.usage.prompt_tokens if response.usage else 0
    completion_tokens = response.usage.completion_tokens if response.usage else 0

    cost = _estimate_cost(model_name, prompt_tokens, completion_tokens)

    logger.info(
        "OpenAI generation: model=%s, prompt_tokens=%d, completion_tokens=%d, cost=$%.6f",
        model_name, prompt_tokens, completion_tokens, cost,
    )

    return LLMResult(
        text=text,
        model=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost_usd=cost,
    )
