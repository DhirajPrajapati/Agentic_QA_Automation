"""
test_llm_client — Tests for tools/llm_client.py mock/real LLM wrapping.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
import importlib
import json

import pytest


@pytest.fixture
def llm_client_mock_mode(monkeypatch):
    """Reload tools.llm_client with USE_MOCK_LLM=true and no real API key."""
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "placeholder_add_org_key_later")
    import tools.llm_client as llm_client

    importlib.reload(llm_client)
    return llm_client


@pytest.mark.parametrize(
    "agent_type",
    ["analysis", "test_case", "test_script_api", "self_heal"],
)
def test_mock_response_is_valid_json_per_agent_type(llm_client_mock_mode, agent_type):
    response = llm_client_mock_mode.invoke_with_retry(
        messages=[{"role": "user", "content": "x"}], agent_type=agent_type
    )
    parsed = json.loads(response)
    assert parsed is not None


def test_test_script_ui_mock_is_valid_python_with_test_functions(llm_client_mock_mode):
    response = llm_client_mock_mode.invoke_with_retry(messages=[], agent_type="test_script_ui")
    compile(response, "<mock test_script_ui>", "exec")
    assert response.count("def test_") >= 2


def test_test_script_ui_mock_reuses_recording_selectors(llm_client_mock_mode):
    response = llm_client_mock_mode.invoke_with_retry(messages=[], agent_type="test_script_ui")
    assert 'input[name="email"]' in response
    assert 'input[name="password"]' in response


def test_test_script_api_mock_adds_negative_cases_to_original_collection(llm_client_mock_mode):
    response = llm_client_mock_mode.invoke_with_retry(messages=[], agent_type="test_script_api")
    parsed = json.loads(response)
    assert "item" in parsed
    assert len(parsed["item"]) > 2  # more than the original 2 happy-path requests


def test_mock_response_falls_back_to_generic_for_unknown_agent_type(llm_client_mock_mode):
    response = llm_client_mock_mode.invoke_with_retry(messages=[], agent_type="unknown_agent")
    json.loads(response)


def test_mock_mode_requires_no_api_key(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import tools.llm_client as llm_client

    importlib.reload(llm_client)
    response = llm_client.invoke_with_retry(
        messages=[{"role": "user", "content": "hi"}], agent_type="analysis"
    )
    json.loads(response)


def test_warns_when_no_real_api_key_set(monkeypatch, caplog):
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "placeholder_add_org_key_later")
    import tools.llm_client as llm_client

    with caplog.at_level("WARNING"):
        importlib.reload(llm_client)
    assert "No real OpenAI key set" in caplog.text


def test_analysis_mock_matches_expected_schema(llm_client_mock_mode):
    response = llm_client_mock_mode.invoke_with_retry(messages=[], agent_type="analysis")
    parsed = json.loads(response)
    assert isinstance(parsed["flows_to_test"], list) and len(parsed["flows_to_test"]) > 0
    assert isinstance(parsed["skip_api"], bool)
    assert isinstance(parsed["risk_areas"], list)
    assert isinstance(parsed["user_types_in_scope"], list)


def test_test_case_mock_matches_expected_schema(llm_client_mock_mode):
    response = llm_client_mock_mode.invoke_with_retry(messages=[], agent_type="test_case")
    parsed = json.loads(response)
    assert isinstance(parsed, list)
    assert len(parsed) >= 2
    required_keys = {
        "jira_id", "test_case_id", "module", "sub_module", "priority", "type",
        "test_case_description", "preconditions", "test_steps", "expected_results",
        "postconditions", "tags", "automation_status", "remarks", "scenario_nature",
        "negative_category",
    }
    for tc in parsed:
        assert required_keys <= tc.keys()
    assert any(tc["priority"] == "HIGH" for tc in parsed)
    assert all(tc["automation_status"] == "Auto-Generated" for tc in parsed)


def test_real_mode_uses_openai_when_key_present(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-key-for-test")
    import tools.llm_client as llm_client

    importlib.reload(llm_client)

    calls = {}

    def fake_real_invoke(messages):
        calls["messages"] = messages
        return "real response"

    monkeypatch.setattr(llm_client, "_real_invoke", fake_real_invoke)
    result = llm_client.invoke_with_retry(
        messages=[{"role": "user", "content": "hi"}], agent_type="analysis"
    )
    assert result == "real response"
    assert calls["messages"] == [{"role": "user", "content": "hi"}]


def test_real_mode_retries_on_rate_limit_then_succeeds(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-key-for-test")
    import tools.llm_client as llm_client

    importlib.reload(llm_client)
    monkeypatch.setattr(llm_client.time, "sleep", lambda seconds: None)

    from openai import APIStatusError
    import httpx

    attempts = {"count": 0}

    def flaky_real_invoke(messages):
        attempts["count"] += 1
        if attempts["count"] < 3:
            request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
            response = httpx.Response(429, request=request, json={"error": {"message": "rate limited"}})
            raise APIStatusError("rate limited", response=response, body=None)
        return "success after retries"

    monkeypatch.setattr(llm_client, "_real_invoke", flaky_real_invoke)
    result = llm_client.invoke_with_retry(messages=[{"role": "user", "content": "hi"}], max_attempts=3)
    assert result == "success after retries"
    assert attempts["count"] == 3


def test_use_mock_llm_reflects_env_var_at_call_time_not_just_import_time(monkeypatch):
    # Simulate a prior test/process having loaded the module in real mode.
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-key-for-test")
    import tools.llm_client as llm_client

    importlib.reload(llm_client)

    # Flip back to mock mode WITHOUT reloading the module again — this is
    # what happens when another module already imported invoke_with_retry.
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    response = llm_client.invoke_with_retry(messages=[], agent_type="analysis")
    json.loads(response)


def test_real_mode_raises_after_exhausting_retries(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-key-for-test")
    import tools.llm_client as llm_client

    importlib.reload(llm_client)
    monkeypatch.setattr(llm_client.time, "sleep", lambda seconds: None)

    from openai import APIStatusError
    import httpx

    def always_fails(messages):
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        response = httpx.Response(429, request=request, json={"error": {"message": "rate limited"}})
        raise APIStatusError("rate limited", response=response, body=None)

    monkeypatch.setattr(llm_client, "_real_invoke", always_fails)
    with pytest.raises(llm_client.LLMRetryError):
        llm_client.invoke_with_retry(messages=[{"role": "user", "content": "hi"}], max_attempts=3)
