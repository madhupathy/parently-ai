"""Tests for Gemini service and LLM result handling."""

from __future__ import annotations

from services.gemini import LLMResult, _estimate_cost


class TestEstimateCost:
    """Tests for cost estimation logic."""

    def test_gemini_flash_cost(self) -> None:
        cost = _estimate_cost("gemini-flash-latest", prompt_tokens=1000, completion_tokens=500)
        # 1000 * 0.075/1M + 500 * 0.30/1M = 0.000075 + 0.00015 = 0.000225
        assert abs(cost - 0.000225) < 1e-8

    def test_gpt4o_mini_cost(self) -> None:
        cost = _estimate_cost("gpt-4o-mini", prompt_tokens=1000, completion_tokens=500)
        # 1000 * 0.15/1M + 500 * 0.60/1M = 0.00015 + 0.0003 = 0.00045
        assert abs(cost - 0.00045) < 1e-8

    def test_unknown_model_returns_zero(self) -> None:
        cost = _estimate_cost("unknown-model", prompt_tokens=1000, completion_tokens=500)
        assert cost == 0.0

    def test_zero_tokens_returns_zero(self) -> None:
        cost = _estimate_cost("gemini-flash-latest", prompt_tokens=0, completion_tokens=0)
        assert cost == 0.0


class TestLLMResult:
    """Tests for LLMResult dataclass."""

    def test_defaults(self) -> None:
        result = LLMResult(text="hello", model="gemini-flash-latest")
        assert result.text == "hello"
        assert result.model == "gemini-flash-latest"
        assert result.prompt_tokens == 0
        assert result.completion_tokens == 0
        assert result.estimated_cost_usd == 0.0

    def test_with_usage(self) -> None:
        result = LLMResult(
            text="digest",
            model="gemini-flash-latest",
            prompt_tokens=500,
            completion_tokens=200,
            estimated_cost_usd=0.0001,
        )
        assert result.prompt_tokens == 500
        assert result.completion_tokens == 200
        assert result.estimated_cost_usd == 0.0001
