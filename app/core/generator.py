import json
import uuid
from datetime import datetime
from groq import Groq
from app.config import settings
from app.models.pipeline import (
    MergedData, DDRReport, AreaSection,
    SeverityItem, ActionItem, SeverityLevel
)
from app.utils.logger import logger

client = Groq(api_key=settings.groq_api_key)

MAX_CHARS = 4000

def _truncate(text: str) -> str:
    if len(text) <= MAX_CHARS:
        return text
    half = MAX_CHARS // 2
    return text[:half] + "\n...[truncated]...\n" + text[-half:]


DDR_GENERATION_PROMPT = """You are a professional building diagnostics report writer.
Generate a complete DDR report from the merged findings below.
Write in simple, professional, CLIENT-FRIENDLY language.

Return ONLY valid JSON:
{{
  "section_1_summary": "2-3 paragraph executive summary of all issues",
  "section_2_area_wise": [
    {{
      "area_name": "string",
      "observations": ["visual inspection points"],
      "thermal_findings": ["thermal finding points"],
      "has_conflict": false,
      "conflict_note": null
    }}
  ],
  "section_3_root_cause": "paragraph explaining probable root causes",
  "section_4_severity": [
    {{
      "area_name": "string",
      "severity": "Low | Medium | High | Critical",
      "reasoning": "why this severity"
    }}
  ],
  "section_5_actions": [
    {{
      "area_name": "string",
      "priority": "Immediate | Short-term | Long-term",
      "action": "specific action",
      "timeline": "e.g. Within 24 hours"
    }}
  ],
  "section_6_notes": "additional observations and recommendations",
  "section_7_missing": ["missing or unclear information"]
}}

Rules:
- Use EXACT property_name, property_address, inspection_date from the data
- Be specific about each area — reference actual findings
- Justify every severity rating with specific evidence
- Never invent facts not in the data
- Write "Not Available" only if truly missing from source
- Deduplicate — never repeat same point twice
- Client-friendly language — no jargon

MERGED FINDINGS:
{merged_json}
"""


def generate_ddr(merged: MergedData) -> DDRReport:
    logger.info("Starting DDR report generation...")

    merged_summary = {
        "property_name": merged.property_name,
        "property_address": merged.property_address,
        "inspection_date": merged.inspection_date,
        "areas": [
            {
                "area_name": a.area_name,
                "inspection_observations": a.inspection_observations[:3],
                "thermal_observations": a.thermal_observations[:3],
                "combined_summary": a.combined_summary,
                "severity": a.severity,
                "severity_reasoning": a.severity_reasoning,
                "probable_root_cause": a.probable_root_cause,
                "recommended_actions": a.recommended_actions[:3],
                "has_conflict": a.has_conflict,
            }
            for a in merged.areas[:8]
        ],
        "conflicts": [
            {
                "area_name": c.area_name,
                "inspection_says": c.inspection_says,
                "thermal_says": c.thermal_says,
                "conflict_description": c.conflict_description,
            }
            for c in merged.conflicts
        ],
        "global_missing": merged.global_missing,
    }

    merged_json = _truncate(json.dumps(merged_summary, indent=2))
    prompt = DDR_GENERATION_PROMPT.format(merged_json=merged_json)
    logger.info(f"DDR prompt length: {len(prompt)} chars")

    try:
        raw = ""
        for attempt in range(3):
            response = client.chat.completions.create(
                model=settings.groq_model_generate,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=4000,
            )
            raw = response.choices[0].message.content.strip()
            if raw:
                break
            logger.warning(f"Empty generator response attempt {attempt+1}")
            prompt = prompt[:int(len(prompt)*0.75)]

        if not raw:
            raise ValueError("Empty response from Groq generator after 3 attempts")

        if "```" in raw:
            for part in raw.split("```"):
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                try:
                    data = json.loads(part)
                    return _build_ddr(data, merged)
                except Exception:
                    continue

        data = json.loads(raw)
        return _build_ddr(data, merged)

    except Exception as e:
        logger.error(f"DDR generation failed: {e}")
        raise


def _build_ddr(data: dict, merged: MergedData) -> DDRReport:
    """Build DDRReport and re-attach images to area sections."""

    # Build image map from merged areas
    area_img_map = {a.area_name.lower(): a.images for a in merged.areas}

    area_sections = []
    for s in data.get("section_2_area_wise", []):
        area_name = s.get("area_name", "")
        # Find images — exact then fuzzy match
        images = area_img_map.get(area_name.lower(), [])
        if not images:
            for k, imgs in area_img_map.items():
                if k in area_name.lower() or area_name.lower() in k:
                    images = imgs
                    break

        area_sections.append(AreaSection(
            area_name=area_name,
            observations=s.get("observations", []),
            thermal_findings=s.get("thermal_findings", []),
            images=images,
            has_conflict=s.get("has_conflict", False),
            conflict_note=s.get("conflict_note"),
        ))

    severity_items = [
        SeverityItem(
            area_name=s.get("area_name", ""),
            severity=SeverityLevel(s.get("severity", "Not Available")),
            reasoning=s.get("reasoning", ""),
        )
        for s in data.get("section_4_severity", [])
    ]

    action_items = [
        ActionItem(
            area_name=a.get("area_name", ""),
            priority=a.get("priority", "Short-term"),
            action=a.get("action", ""),
            timeline=a.get("timeline", ""),
        )
        for a in data.get("section_5_actions", [])
    ]

    ddr = DDRReport(
        report_id=str(uuid.uuid4()),
        generated_at=datetime.now().strftime("%d %B %Y, %H:%M"),
        property_name=merged.property_name,
        property_address=merged.property_address,
        inspection_date=merged.inspection_date,
        section_1_summary=data.get("section_1_summary", ""),
        section_2_area_wise=area_sections,
        section_3_root_cause=data.get("section_3_root_cause", ""),
        section_4_severity=severity_items,
        section_5_actions=action_items,
        section_6_notes=data.get("section_6_notes", ""),
        section_7_missing=data.get("section_7_missing", []),
    )

    logger.info(
        f"DDR generation complete: {len(area_sections)} areas, "
        f"{len(severity_items)} severity items, {len(action_items)} actions"
    )
    return ddr


def debug_image_counts(ddr: DDRReport):
    """Log image counts per area for debugging."""
    total = sum(len(a.images) for a in ddr.section_2_area_wise)
    logger.info(f"DEBUG images in DDR sections: total={total}")
    for area in ddr.section_2_area_wise:
        logger.info(f"  Area '{area.area_name}': {len(area.images)} images")