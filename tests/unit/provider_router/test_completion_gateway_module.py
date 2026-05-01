from __future__ import annotations

from unittest.mock import patch

from swallow.provider_router import completion_gateway
from swallow.provider_router._http_helpers import AgentLLMResponse
from swallow.provider_router.agent_llm import call_agent_llm
from swallow.provider_router.router import invoke_completion as router_invoke_completion


def test_completion_gateway_is_reexported_by_router_facade() -> None:
    assert router_invoke_completion is completion_gateway.invoke_completion


def test_call_agent_llm_uses_completion_gateway_lazy_import() -> None:
    response = AgentLLMResponse(content="ok", input_tokens=3, output_tokens=5, model="mock-model")

    with patch("swallow.provider_router.completion_gateway.invoke_completion", return_value=response) as invoke:
        returned = call_agent_llm("hello", system="be terse", model="explicit-model", timeout_seconds=9)

    assert returned is response
    invoke.assert_called_once_with(
        "hello",
        system="be terse",
        model="explicit-model",
        timeout_seconds=9,
    )
