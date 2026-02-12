"""NBCU Agent – processes JSON schedule files for NBCU."""

from agents.base_agent import BaseProviderAgent


class NBCUAgent(BaseProviderAgent):
    provider_name = "NBCU"
    file_extensions = [".json"]
