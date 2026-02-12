"""CBS Agent – processes CSV schedule files for CBS."""

from agents.base_agent import BaseProviderAgent


class CBSAgent(BaseProviderAgent):
    provider_name = "CBS"
    file_extensions = [".csv"]
