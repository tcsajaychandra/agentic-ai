"""Tests for the Bedrock LLM client utility."""

from unittest.mock import patch
from agents.bedrock_llm import _has_credentials, get_supervisor_llm, get_agent_llm


class TestHasCredentials:
    @patch("agents.bedrock_llm.AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
    @patch("agents.bedrock_llm.AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    def test_dummy_credentials_return_false(self):
        assert _has_credentials() is False

    @patch("agents.bedrock_llm.AWS_ACCESS_KEY_ID", "")
    @patch("agents.bedrock_llm.AWS_SECRET_ACCESS_KEY", "")
    def test_empty_credentials_return_false(self):
        assert _has_credentials() is False

    @patch("agents.bedrock_llm.AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7REAL")
    @patch("agents.bedrock_llm.AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYREALKEY")
    def test_real_credentials_return_true(self):
        assert _has_credentials() is True


class TestGetLLMFunctions:
    @patch("agents.bedrock_llm._has_credentials", return_value=False)
    def test_supervisor_llm_returns_none_without_creds(self, mock_creds):
        assert get_supervisor_llm() is None

    @patch("agents.bedrock_llm._has_credentials", return_value=False)
    def test_agent_llm_returns_none_without_creds(self, mock_creds):
        assert get_agent_llm() is None
