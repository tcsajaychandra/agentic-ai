"""
Unified parser that reads JSON, CSV, and TXT schedule files
and normalizes them into a common event structure.
"""

import json
import csv
import os
from typing import List, Dict, Any


class UnifiedParser:
    """Parses schedule files from multiple providers into a normalized format."""

    REQUIRED_FIELDS = [
        "event_id", "title", "channel", "start_time",
        "end_time", "program_type", "content_id",
    ]

    @staticmethod
    def parse_file(file_path: str) -> Dict[str, Any]:
        ext = os.path.splitext(file_path)[1].lower()
        parser_map = {
            ".json": UnifiedParser.parse_json,
            ".csv": UnifiedParser.parse_csv,
            ".txt": UnifiedParser.parse_txt,
        }
        parser_fn = parser_map.get(ext)
        if parser_fn is None:
            raise ValueError(f"Unsupported file format: {ext}")
        return parser_fn(file_path)

    @staticmethod
    def parse_json(file_path: str) -> Dict[str, Any]:
        with open(file_path, "r") as f:
            data = json.load(f)

        provider = data.get("provider", "Unknown")
        events = []
        for evt in data.get("events", []):
            events.append(UnifiedParser._normalize_event(evt, provider))
        return {"provider": provider, "source_file": file_path, "events": events}

    @staticmethod
    def parse_csv(file_path: str) -> Dict[str, Any]:
        events = []
        provider = "Unknown"
        with open(file_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Infer provider from event_id prefix
                eid = row.get("event_id", "")
                if "-" in eid:
                    provider = eid.split("-")[0]

                blackout_raw = row.get("blackout_regions", "")
                blackout = [r.strip() for r in blackout_raw.split("|") if r.strip()]
                evt = {
                    "event_id": row.get("event_id", ""),
                    "title": row.get("title", ""),
                    "channel": row.get("channel", ""),
                    "start_time": row.get("start_time", ""),
                    "end_time": row.get("end_time", ""),
                    "program_type": row.get("program_type", ""),
                    "blackout_regions": blackout,
                    "content_id": row.get("content_id", ""),
                    "alternate_content": row.get("alternate_content", "") or None,
                }
                events.append(UnifiedParser._normalize_event(evt, provider))
        return {"provider": provider, "source_file": file_path, "events": events}

    @staticmethod
    def parse_txt(file_path: str) -> Dict[str, Any]:
        """Parse pipe-delimited TXT file.

        Expected column order:
        event_id|title|channel|start_time|end_time|program_type|blackout_regions|content_id|alternate_content
        """
        events = []
        provider = "Unknown"
        field_names = [
            "event_id", "title", "channel", "start_time", "end_time",
            "program_type", "blackout_regions", "content_id", "alternate_content",
        ]
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) < len(field_names):
                    parts.extend([""] * (len(field_names) - len(parts)))

                eid = parts[0]
                if "-" in eid:
                    provider = eid.split("-")[0]

                blackout_raw = parts[6]
                blackout = [r.strip() for r in blackout_raw.split(",") if r.strip()]

                evt = {
                    "event_id": parts[0],
                    "title": parts[1],
                    "channel": parts[2],
                    "start_time": parts[3],
                    "end_time": parts[4],
                    "program_type": parts[5],
                    "blackout_regions": blackout,
                    "content_id": parts[7],
                    "alternate_content": parts[8] if parts[8] else None,
                }
                events.append(UnifiedParser._normalize_event(evt, provider))
        return {"provider": provider, "source_file": file_path, "events": events}

    @staticmethod
    def _normalize_event(evt: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """Ensure every event has all required keys with defaults."""
        normalized = {
            "event_id": evt.get("event_id", ""),
            "title": evt.get("title", ""),
            "channel": evt.get("channel", ""),
            "start_time": evt.get("start_time", ""),
            "end_time": evt.get("end_time", ""),
            "program_type": evt.get("program_type", ""),
            "blackout_regions": evt.get("blackout_regions", []),
            "content_id": evt.get("content_id", ""),
            "alternate_content": evt.get("alternate_content"),
            "provider": provider,
        }
        return normalized
