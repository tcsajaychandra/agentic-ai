"""Tests for the UnifiedParser – JSON, CSV, and TXT formats."""

import json
import os
import tempfile
import pytest

from parsers.unified_parser import UnifiedParser


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


# ── JSON parsing ──────────────────────────────────────────────────────────────

class TestJSONParser:
    def _write_json(self, tmp_dir, data):
        path = os.path.join(tmp_dir, "test.json")
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_parse_json_basic(self, tmp_dir):
        data = {
            "provider": "NBCU",
            "events": [
                {
                    "event_id": "E1",
                    "title": "Show A",
                    "channel": "NBC",
                    "start_time": "2026-01-01T00:00:00Z",
                    "end_time": "2026-01-01T01:00:00Z",
                    "program_type": "Sports",
                    "blackout_regions": ["NY"],
                    "content_id": "cid-1",
                    "alternate_content": "Alt Show",
                }
            ],
        }
        path = self._write_json(tmp_dir, data)
        result = UnifiedParser.parse_json(path)

        assert result["provider"] == "NBCU"
        assert len(result["events"]) == 1
        evt = result["events"][0]
        assert evt["event_id"] == "E1"
        assert evt["title"] == "Show A"
        assert evt["blackout_regions"] == ["NY"]
        assert evt["alternate_content"] == "Alt Show"

    def test_parse_json_empty_events(self, tmp_dir):
        data = {"provider": "Test", "events": []}
        path = self._write_json(tmp_dir, data)
        result = UnifiedParser.parse_json(path)
        assert result["events"] == []

    def test_parse_json_missing_optional_fields(self, tmp_dir):
        data = {
            "provider": "X",
            "events": [
                {
                    "event_id": "E2",
                    "title": "Show B",
                    "channel": "CH1",
                    "start_time": "2026-01-01T00:00:00Z",
                    "end_time": "2026-01-01T01:00:00Z",
                    "program_type": "Drama",
                    "content_id": "cid-2",
                }
            ],
        }
        path = self._write_json(tmp_dir, data)
        result = UnifiedParser.parse_json(path)
        evt = result["events"][0]
        assert evt["blackout_regions"] == []
        assert evt["alternate_content"] is None

    def test_parse_file_dispatches_json(self, tmp_dir):
        data = {"provider": "NBCU", "events": []}
        path = self._write_json(tmp_dir, data)
        result = UnifiedParser.parse_file(path)
        assert result["provider"] == "NBCU"


# ── CSV parsing ───────────────────────────────────────────────────────────────

class TestCSVParser:
    def _write_csv(self, tmp_dir, rows):
        path = os.path.join(tmp_dir, "test.csv")
        header = "event_id,title,channel,start_time,end_time,program_type,blackout_regions,content_id,alternate_content\n"
        with open(path, "w") as f:
            f.write(header)
            for row in rows:
                f.write(row + "\n")
        return path

    def test_parse_csv_basic(self, tmp_dir):
        rows = [
            "CBS-001,60 Minutes,CBS,2026-01-01T19:00:00Z,2026-01-01T20:00:00Z,News,,cbs-60m,",
        ]
        path = self._write_csv(tmp_dir, rows)
        result = UnifiedParser.parse_csv(path)

        assert result["provider"] == "CBS"
        assert len(result["events"]) == 1
        evt = result["events"][0]
        assert evt["title"] == "60 Minutes"
        assert evt["blackout_regions"] == []
        assert evt["alternate_content"] is None

    def test_parse_csv_with_blackout(self, tmp_dir):
        rows = [
            "CBS-002,NFL,CBS,2026-01-01T13:00:00Z,2026-01-01T16:00:00Z,Sports,MA|CT,cbs-nfl,Local News",
        ]
        path = self._write_csv(tmp_dir, rows)
        result = UnifiedParser.parse_csv(path)
        evt = result["events"][0]
        assert evt["blackout_regions"] == ["MA", "CT"]
        assert evt["alternate_content"] == "Local News"

    def test_parse_csv_multiple_rows(self, tmp_dir):
        rows = [
            "CBS-001,Show A,CBS,2026-01-01T00:00:00Z,2026-01-01T01:00:00Z,Drama,,cbs-a,",
            "CBS-002,Show B,CBS,2026-01-02T00:00:00Z,2026-01-02T01:00:00Z,Comedy,,cbs-b,",
        ]
        path = self._write_csv(tmp_dir, rows)
        result = UnifiedParser.parse_csv(path)
        assert len(result["events"]) == 2

    def test_parse_file_dispatches_csv(self, tmp_dir):
        rows = ["CBS-001,Test,CBS,2026-01-01T00:00:00Z,2026-01-01T01:00:00Z,News,,cbs-t,"]
        path = self._write_csv(tmp_dir, rows)
        result = UnifiedParser.parse_file(path)
        assert result["provider"] == "CBS"


# ── TXT parsing ───────────────────────────────────────────────────────────────

class TestTXTParser:
    def _write_txt(self, tmp_dir, lines):
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            for line in lines:
                f.write(line + "\n")
        return path

    def test_parse_txt_basic(self, tmp_dir):
        lines = [
            "FOX-001|NASCAR|FOX|2026-01-01T14:00:00Z|2026-01-01T18:00:00Z|Sports|FL,GA|fox-nascar|FOX Highlights",
        ]
        path = self._write_txt(tmp_dir, lines)
        result = UnifiedParser.parse_txt(path)

        assert result["provider"] == "FOX"
        assert len(result["events"]) == 1
        evt = result["events"][0]
        assert evt["title"] == "NASCAR"
        assert evt["blackout_regions"] == ["FL", "GA"]
        assert evt["alternate_content"] == "FOX Highlights"

    def test_parse_txt_no_blackout(self, tmp_dir):
        lines = [
            "FOX-002|Masked Singer|FOX|2026-01-01T20:00:00Z|2026-01-01T21:00:00Z|Entertainment||fox-ms|",
        ]
        path = self._write_txt(tmp_dir, lines)
        result = UnifiedParser.parse_txt(path)
        evt = result["events"][0]
        assert evt["blackout_regions"] == []
        assert evt["alternate_content"] is None

    def test_parse_txt_empty_lines_skipped(self, tmp_dir):
        lines = [
            "FOX-001|Show|FOX|2026-01-01T00:00:00Z|2026-01-01T01:00:00Z|Sports||fox-s|",
            "",
            "FOX-002|Show2|FOX|2026-01-02T00:00:00Z|2026-01-02T01:00:00Z|Drama||fox-s2|",
        ]
        path = self._write_txt(tmp_dir, lines)
        result = UnifiedParser.parse_txt(path)
        assert len(result["events"]) == 2

    def test_parse_file_dispatches_txt(self, tmp_dir):
        lines = ["FOX-001|Test|FOX|2026-01-01T00:00:00Z|2026-01-01T01:00:00Z|News||fox-t|"]
        path = self._write_txt(tmp_dir, lines)
        result = UnifiedParser.parse_file(path)
        assert result["provider"] == "FOX"


# ── Unsupported format ────────────────────────────────────────────────────────

class TestUnsupportedFormat:
    def test_unsupported_extension_raises(self, tmp_dir):
        path = os.path.join(tmp_dir, "test.yaml")
        with open(path, "w") as f:
            f.write("key: value\n")
        with pytest.raises(ValueError, match="Unsupported file format"):
            UnifiedParser.parse_file(path)
