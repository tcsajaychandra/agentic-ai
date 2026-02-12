"""
Base agent class providing shared file-processing logic for all provider agents.
Each provider agent inherits from this and specifies which file extensions it handles.
"""

import os
import glob
from typing import List, Dict, Any

from parsers.unified_parser import UnifiedParser
from parsers.scte224_converter import SCTE224Converter


class BaseProviderAgent:
    """Base class for NBCU, CBS, and Fox agents."""

    provider_name: str = "Unknown"
    file_extensions: List[str] = []

    def __init__(self, source_dir: str, target_dir: str):
        self.source_dir = source_dir
        self.target_dir = target_dir

    def find_files(self) -> List[str]:
        """Find all files in source_dir matching the agent's extensions."""
        matched = []
        for ext in self.file_extensions:
            pattern = os.path.join(self.source_dir, f"*{ext}")
            matched.extend(glob.glob(pattern))
        return sorted(matched)

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

        return {
            "agent": self.provider_name,
            "status": "success" if not errors else "partial_success",
            "files_processed": len(files),
            "source_files": files,
            "output_files": output_files,
            "events_count": len(all_events),
            "events": all_events,
            "errors": errors,
        }
