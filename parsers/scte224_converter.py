"""
Converts normalized schedule events to SCTE-224 (ESAM) compliant XML.

SCTE-224 defines a data model for media policy (blackouts, alternate content,
ad insertion). This converter maps normalized events into the SCTE-224 schema
using ViewingPolicy, Media, MediaPoint, and AudienceProperty elements.
"""

import os
from datetime import datetime
from lxml import etree
from typing import Dict, Any, List


SCTE224_NS = "urn:scte:224:2018"
NSMAP = {"scte224": SCTE224_NS}


class SCTE224Converter:
    """Converts normalized event dicts to SCTE-224 XML documents."""

    @staticmethod
    def convert(parsed_data: Dict[str, Any], output_dir: str) -> str:
        """Convert a parsed provider result to an SCTE-224 XML file.

        Returns the path to the written XML file.
        """
        provider = parsed_data["provider"]
        events = parsed_data["events"]
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

        root = etree.Element(
            f"{{{SCTE224_NS}}}SCTE224",
            nsmap=NSMAP,
        )
        root.set("provider", provider)
        root.set("generatedAt", datetime.utcnow().isoformat() + "Z")

        for evt in events:
            SCTE224Converter._add_media(root, evt)

        for evt in events:
            if evt.get("blackout_regions"):
                SCTE224Converter._add_viewing_policy(root, evt)

        os.makedirs(output_dir, exist_ok=True)
        filename = f"{provider.lower()}_scte224_{timestamp}.xml"
        output_path = os.path.join(output_dir, filename)

        tree = etree.ElementTree(root)
        tree.write(output_path, pretty_print=True, xml_declaration=True, encoding="UTF-8")
        return output_path

    @staticmethod
    def convert_events(events: List[Dict[str, Any]], provider: str, output_dir: str) -> str:
        """Convenience wrapper that accepts a list of events directly."""
        parsed_data = {"provider": provider, "events": events}
        return SCTE224Converter.convert(parsed_data, output_dir)

    @staticmethod
    def _add_media(root: etree._Element, evt: Dict[str, Any]) -> None:
        media = etree.SubElement(root, f"{{{SCTE224_NS}}}Media")
        media.set("id", evt["content_id"])
        media.set("description", evt["title"])

        media_point_start = etree.SubElement(media, f"{{{SCTE224_NS}}}MediaPoint")
        media_point_start.set("id", f"{evt['content_id']}_start")
        media_point_start.set("matchTime", evt["start_time"])
        media_point_start.set("type", "start")

        media_point_end = etree.SubElement(media, f"{{{SCTE224_NS}}}MediaPoint")
        media_point_end.set("id", f"{evt['content_id']}_end")
        media_point_end.set("matchTime", evt["end_time"])
        media_point_end.set("type", "end")

        channel_el = etree.SubElement(media, f"{{{SCTE224_NS}}}Channel")
        channel_el.set("name", evt["channel"])

        program_el = etree.SubElement(media, f"{{{SCTE224_NS}}}ProgramType")
        program_el.text = evt["program_type"]

    @staticmethod
    def _add_viewing_policy(root: etree._Element, evt: Dict[str, Any]) -> None:
        policy = etree.SubElement(root, f"{{{SCTE224_NS}}}ViewingPolicy")
        policy.set("id", f"policy_{evt['event_id']}")
        policy.set("mediaId", evt["content_id"])

        for region in evt["blackout_regions"]:
            audience = etree.SubElement(policy, f"{{{SCTE224_NS}}}AudienceProperty")
            audience.set("type", "blackout")
            audience.set("region", region)

        if evt.get("alternate_content"):
            alt = etree.SubElement(policy, f"{{{SCTE224_NS}}}AlternateContent")
            alt.set("description", evt["alternate_content"])

    @staticmethod
    def read_output(file_path: str) -> str:
        """Read an SCTE-224 XML file and return its contents as a string."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
