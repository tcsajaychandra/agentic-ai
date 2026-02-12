"""Fox Agent – processes TXT (pipe-delimited) schedule files for Fox."""

from agents.base_agent import BaseProviderAgent


class FoxAgent(BaseProviderAgent):
    provider_name = "FOX"
    file_extensions = [".txt"]
