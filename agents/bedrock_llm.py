"""
AWS Bedrock LLM client utility.

Provides factory functions that return LangChain ChatBedrockConverse
instances for the supervisor (Nova Pro) and sub-agents (Nova Lite).

All credentials are loaded from .env via python-dotenv.
If credentials are missing or Bedrock is unreachable the helpers
return None so callers can fall back to non-LLM mode gracefully.
"""

import os
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

SUPERVISOR_MODEL_ID = os.getenv("BEDROCK_SUPERVISOR_MODEL_ID", "amazon.nova-pro-v1:0")
AGENT_MODEL_ID = os.getenv("BEDROCK_AGENT_MODEL_ID", "amazon.nova-lite-v1:0")


def _has_credentials() -> bool:
    """Return True if real AWS credentials appear to be configured."""
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        return False
    if "EXAMPLE" in AWS_ACCESS_KEY_ID or "EXAMPLE" in AWS_SECRET_ACCESS_KEY:
        return False
    return True


def get_supervisor_llm():
    """Return a ChatBedrockConverse instance using Amazon Nova Pro.

    Returns None when credentials are not configured.
    """
    if not _has_credentials():
        return None
    try:
        from langchain_aws import ChatBedrockConverse
        return ChatBedrockConverse(
            model=SUPERVISOR_MODEL_ID,
            region_name=AWS_REGION,
            credentials_profile_name=None,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            temperature=0.3,
            max_tokens=2048,
        )
    except Exception:
        return None


def get_agent_llm():
    """Return a ChatBedrockConverse instance using Amazon Nova Lite.

    Returns None when credentials are not configured.
    """
    if not _has_credentials():
        return None
    try:
        from langchain_aws import ChatBedrockConverse
        return ChatBedrockConverse(
            model=AGENT_MODEL_ID,
            region_name=AWS_REGION,
            credentials_profile_name=None,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            temperature=0.2,
            max_tokens=1024,
        )
    except Exception:
        return None
