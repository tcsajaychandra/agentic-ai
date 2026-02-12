"""Tests for the SCTE224Converter – XML generation and structure."""

import os
import tempfile
import pytest
from lxml import etree

from parsers.scte224_converter import SCTE224Converter, SCTE224_NS


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_parsed_data():
    return {
        "provider": "NBCU",
        "events": [
            {
                "event_id": "NBCU-001",
                "title": "Sunday Night Football",
                "channel": "NBC",
                "start_time": "2026-02-15T20:00:00Z",
                "end_time": "2026-02-15T23:30:00Z",
                "program_type": "Sports",
                "blackout_regions": ["NY", "NJ"],
                "content_id": "nbcu-snf",
                "alternate_content": "Local News",
                "provider": "NBCU",
            },
            {
                "event_id": "NBCU-002",
                "title": "Tonight Show",
                "channel": "NBC",
                "start_time": "2026-02-16T00:00:00Z",
                "end_time": "2026-02-16T01:00:00Z",
                "program_type": "Entertainment",
                "blackout_regions": [],
                "content_id": "nbcu-ts",
                "alternate_content": None,
                "provider": "NBCU",
            },
        ],
    }


class TestSCTE224Converter:
    def test_convert_creates_file(self, tmp_dir, sample_parsed_data):
        path = SCTE224Converter.convert(sample_parsed_data, tmp_dir)
        assert os.path.exists(path)
        assert path.endswith(".xml")

    def test_output_is_valid_xml(self, tmp_dir, sample_parsed_data):
        path = SCTE224Converter.convert(sample_parsed_data, tmp_dir)
        tree = etree.parse(path)
        root = tree.getroot()
        assert root.tag == f"{{{SCTE224_NS}}}SCTE224"

    def test_provider_attribute(self, tmp_dir, sample_parsed_data):
        path = SCTE224Converter.convert(sample_parsed_data, tmp_dir)
        tree = etree.parse(path)
        root = tree.getroot()
        assert root.get("provider") == "NBCU"

    def test_media_elements_count(self, tmp_dir, sample_parsed_data):
        path = SCTE224Converter.convert(sample_parsed_data, tmp_dir)
        tree = etree.parse(path)
        root = tree.getroot()
        media_elements = root.findall(f"{{{SCTE224_NS}}}Media")
        assert len(media_elements) == 2

    def test_media_has_media_points(self, tmp_dir, sample_parsed_data):
        path = SCTE224Converter.convert(sample_parsed_data, tmp_dir)
        tree = etree.parse(path)
        root = tree.getroot()
        media = root.findall(f"{{{SCTE224_NS}}}Media")[0]
        points = media.findall(f"{{{SCTE224_NS}}}MediaPoint")
        assert len(points) == 2
        types = {p.get("type") for p in points}
        assert types == {"start", "end"}

    def test_viewing_policy_for_blackout(self, tmp_dir, sample_parsed_data):
        path = SCTE224Converter.convert(sample_parsed_data, tmp_dir)
        tree = etree.parse(path)
        root = tree.getroot()
        policies = root.findall(f"{{{SCTE224_NS}}}ViewingPolicy")
        # Only the first event has blackout_regions
        assert len(policies) == 1
        assert policies[0].get("mediaId") == "nbcu-snf"

    def test_audience_properties(self, tmp_dir, sample_parsed_data):
        path = SCTE224Converter.convert(sample_parsed_data, tmp_dir)
        tree = etree.parse(path)
        root = tree.getroot()
        policy = root.findall(f"{{{SCTE224_NS}}}ViewingPolicy")[0]
        audiences = policy.findall(f"{{{SCTE224_NS}}}AudienceProperty")
        regions = {a.get("region") for a in audiences}
        assert regions == {"NY", "NJ"}

    def test_alternate_content_element(self, tmp_dir, sample_parsed_data):
        path = SCTE224Converter.convert(sample_parsed_data, tmp_dir)
        tree = etree.parse(path)
        root = tree.getroot()
        policy = root.findall(f"{{{SCTE224_NS}}}ViewingPolicy")[0]
        alt = policy.find(f"{{{SCTE224_NS}}}AlternateContent")
        assert alt is not None
        assert alt.get("description") == "Local News"

    def test_no_viewing_policy_without_blackout(self, tmp_dir):
        data = {
            "provider": "FOX",
            "events": [
                {
                    "event_id": "FOX-001",
                    "title": "Show",
                    "channel": "FOX",
                    "start_time": "2026-01-01T00:00:00Z",
                    "end_time": "2026-01-01T01:00:00Z",
                    "program_type": "Drama",
                    "blackout_regions": [],
                    "content_id": "fox-1",
                    "alternate_content": None,
                    "provider": "FOX",
                }
            ],
        }
        path = SCTE224Converter.convert(data, tmp_dir)
        tree = etree.parse(path)
        root = tree.getroot()
        policies = root.findall(f"{{{SCTE224_NS}}}ViewingPolicy")
        assert len(policies) == 0

    def test_read_output(self, tmp_dir, sample_parsed_data):
        path = SCTE224Converter.convert(sample_parsed_data, tmp_dir)
        content = SCTE224Converter.read_output(path)
        assert "SCTE224" in content
        assert "nbcu-snf" in content

    def test_convert_events_shortcut(self, tmp_dir):
        events = [
            {
                "event_id": "T-001",
                "title": "Test Event",
                "channel": "CH1",
                "start_time": "2026-01-01T00:00:00Z",
                "end_time": "2026-01-01T01:00:00Z",
                "program_type": "News",
                "blackout_regions": [],
                "content_id": "t-1",
                "alternate_content": None,
                "provider": "TEST",
            }
        ]
        path = SCTE224Converter.convert_events(events, "TEST", tmp_dir)
        assert os.path.exists(path)
