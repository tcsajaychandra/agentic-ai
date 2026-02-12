"""Tests for the agent system – individual agents and supervisor."""

import os
import json
import tempfile
import pytest

from agents.nbcu_agent import NBCUAgent
from agents.cbs_agent import CBSAgent
from agents.fox_agent import FoxAgent
from agents.supervisor import SupervisorAgent


@pytest.fixture
def setup_dirs():
    """Create temp source and target dirs with sample data files."""
    with tempfile.TemporaryDirectory() as base:
        src = os.path.join(base, "source")
        tgt = os.path.join(base, "target")
        os.makedirs(src)
        os.makedirs(tgt)

        # JSON file (NBCU)
        json_data = {
            "provider": "NBCU",
            "events": [
                {
                    "event_id": "NBCU-001",
                    "title": "Test Show",
                    "channel": "NBC",
                    "start_time": "2026-01-01T00:00:00Z",
                    "end_time": "2026-01-01T01:00:00Z",
                    "program_type": "Sports",
                    "blackout_regions": ["NY"],
                    "content_id": "nbcu-test",
                    "alternate_content": "Alt",
                }
            ],
        }
        with open(os.path.join(src, "nbcu.json"), "w") as f:
            json.dump(json_data, f)

        # CSV file (CBS)
        csv_content = (
            "event_id,title,channel,start_time,end_time,program_type,blackout_regions,content_id,alternate_content\n"
            "CBS-001,CBS Show,CBS,2026-01-01T19:00:00Z,2026-01-01T20:00:00Z,News,,cbs-test,\n"
        )
        with open(os.path.join(src, "cbs.csv"), "w") as f:
            f.write(csv_content)

        # TXT file (FOX)
        txt_content = "FOX-001|FOX Show|FOX|2026-01-01T14:00:00Z|2026-01-01T18:00:00Z|Sports|FL|fox-test|Alt Show\n"
        with open(os.path.join(src, "fox.txt"), "w") as f:
            f.write(txt_content)

        yield src, tgt


class TestNBCUAgent:
    def test_finds_json_files(self, setup_dirs):
        src, tgt = setup_dirs
        agent = NBCUAgent(src, tgt)
        files = agent.find_files()
        assert len(files) == 1
        assert files[0].endswith(".json")

    def test_process_produces_output(self, setup_dirs):
        src, tgt = setup_dirs
        agent = NBCUAgent(src, tgt)
        result = agent.process()
        assert result["agent"] == "NBCU"
        assert result["files_processed"] == 1
        assert result["events_count"] == 1
        assert len(result["output_files"]) == 1


class TestCBSAgent:
    def test_finds_csv_files(self, setup_dirs):
        src, tgt = setup_dirs
        agent = CBSAgent(src, tgt)
        files = agent.find_files()
        assert len(files) == 1
        assert files[0].endswith(".csv")

    def test_process_produces_output(self, setup_dirs):
        src, tgt = setup_dirs
        agent = CBSAgent(src, tgt)
        result = agent.process()
        assert result["agent"] == "CBS"
        assert result["files_processed"] == 1
        assert result["events_count"] == 1


class TestFoxAgent:
    def test_finds_txt_files(self, setup_dirs):
        src, tgt = setup_dirs
        agent = FoxAgent(src, tgt)
        files = agent.find_files()
        assert len(files) == 1
        assert files[0].endswith(".txt")

    def test_process_produces_output(self, setup_dirs):
        src, tgt = setup_dirs
        agent = FoxAgent(src, tgt)
        result = agent.process()
        assert result["agent"] == "FOX"
        assert result["files_processed"] == 1
        assert result["events_count"] == 1


class TestSupervisorAgent:
    def test_run_returns_combined_results(self, setup_dirs):
        src, tgt = setup_dirs
        supervisor = SupervisorAgent(src, tgt)
        results = supervisor.run()

        assert results["total_files_processed"] == 3
        assert results["total_events"] == 3
        assert results["total_output_files"] == 3
        assert results["status"] in ("success", "partial_success")
        assert len(results["agent_results"]) == 3

    def test_run_creates_xml_files(self, setup_dirs):
        src, tgt = setup_dirs
        supervisor = SupervisorAgent(src, tgt)
        supervisor.run()

        xml_files = [f for f in os.listdir(tgt) if f.endswith(".xml")]
        assert len(xml_files) == 3

    def test_no_files_scenario(self):
        with tempfile.TemporaryDirectory() as base:
            src = os.path.join(base, "empty_src")
            tgt = os.path.join(base, "empty_tgt")
            os.makedirs(src)
            os.makedirs(tgt)
            supervisor = SupervisorAgent(src, tgt)
            results = supervisor.run()
            assert results["total_files_processed"] == 0
            assert results["total_events"] == 0
