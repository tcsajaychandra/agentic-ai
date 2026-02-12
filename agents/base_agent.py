"""
Base agent class providing shared file-processing logic for all provider agents.
Each provider agent inherits from this and specifies which file extensions it handles.

When AWS Bedrock credentials are configured, each agent uses Amazon Nova Lite
to generate an intelligent analysis of every converted event batch (e.g.
blackout impact, scheduling conflicts, SCTE-224 compliance notes).
When credentials are absent the agent still works in deterministic mode.
"""

import json
import os
import glob
from typing import List, Dict, Any

from parsers.unified_parser import UnifiedParser
from parsers.scte224_converter import SCTE224Converter
from agents.bedrock_llm import get_agent_llm


AGENT_ANALYSIS_PROMPT = """You are a media scheduling analyst for the {provider} network.
You have been given the following events that were just converted to SCTE-224 format.

Events:
{events_json}

Provide a brief analysis covering:
1. Total number of events and their types (Sports, Entertainment, News, etc.)
2. Blackout regions identified and their potential viewer impact
3. Any scheduling observations (overlapping times, prime-time placements, etc.)
4. SCTE-224 compliance notes (alternate content availability for blackouts)

Keep the response concise (4-6 sentences)."""


class BaseProviderAgent:
    """Base class for NBCU, CBS, and Fox agents."""

    provider_name: str = "Unknown"
    file_extensions: List[str] = []

    def __init__(self, source_dir: str, target_dir: str):
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.llm = get_agent_llm()

    def find_files(self) -> List[str]:
        """Find all files in source_dir matching the agent's extensions."""
        matched = []
        for ext in self.file_extensions:
            pattern = os.path.join(self.source_dir, f"*{ext}")
            matched.extend(glob.glob(pattern))
        return sorted(matched)

    def _llm_analyze(self, events: List[Dict[str, Any]]) -> str:
        """Use Nova Lite to generate an analysis of the converted events.

        Returns an empty string when the LLM is unavailable.
        """
        if self.llm is None or not events:
            return ""
        try:
            events_summary = json.dumps(events, indent=2, default=str)
            prompt = AGENT_ANALYSIS_PROMPT.format(
                provider=self.provider_name,
                events_json=events_summary,
            )
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            return f"[LLM analysis unavailable: {e}]"

    def process(self) -> Dict[str, Any]:
        """Parse source files, convert to SCTE-224, return results summary."""
        files = self.find_files()
        if not files:
            return {
                "agent": self.provider_name,
                "status": "no_files_found",
                "files_processed": 0,
                "output_files": [],
                "events": [],
                "errors": [],
                "llm_analysis": "",
            }

        all_events = []
        output_files = []
        errors = []

        for fpath in files:
            try:
                parsed = UnifiedParser.parse_file(fpath)
                events = parsed["events"]
                all_events.extend(events)

                output_path = SCTE224Converter.convert(parsed, self.target_dir)
                output_files.append(output_path)
            except Exception as e:
                errors.append({"file": fpath, "error": str(e)})

        # Use Nova Lite LLM for intelligent analysis
        llm_analysis = self._llm_analyze(all_events)

        return {
            "agent": self.provider_name,
            "status": "success" if not errors else "partial_success",
            "files_processed": len(files),
            "source_files": files,
            "output_files": output_files,
            "events_count": len(all_events),
            "events": all_events,
            "errors": errors,
            "llm_analysis": llm_analysis,
        }
