import json
from groq import Groq
from app.config import settings
from app.models.pipeline import (
    InspectionData, ThermalData, MergedData,
    MergedAreaFinding, ConflictItem, SeverityLevel
)
from app.utils.logger import logger

client = Groq(api_key=settings.groq_api_key)
MAX_JSON_CHARS = 3000


def _truncate_json(data: dict) -> str:
    text = json.dumps(data, indent=2)
    if len(text) <= MAX_JSON_CHARS:
        return text
    return text[:MAX_JSON_CHARS] + "\n...[truncated]..."


MERGE_PROMPT = """You are a building diagnostics analyst.
Merge inspection and thermal findings into a unified DDR.

IMPORTANT: Compare property names from both documents.
If they are DIFFERENT properties, flag it as a conflict.

Return ONLY valid JSON:
{{
  "property_name": "Use CLIENT name from thermal doc (e.g. XYC Corporation) NOT facility name. If inspection has different name use: InspectionName | ThermalClientName",
  "property_address": "string",
  "inspection_date": "string or Not Available",
  "areas": [
    {{
      "area_name": "string",
      "inspection_observations": ["list"],
      "thermal_observations": ["list"],
      "combined_summary": "string",
      "severity": "Low | Medium | High | Critical | Not Available",
      "severity_reasoning": "string",
      "probable_root_cause": "string",
      "recommended_actions": ["list"],
      "has_conflict": false
    }}
  ],
  "conflicts": [
    {{
      "area_name": "string",
      "inspection_says": "string",
      "thermal_says": "string",
      "conflict_description": "string"
    }}
  ],
  "global_missing": ["list"]
}}

Rules:
- If inspection and thermal are from DIFFERENT properties, add conflict: area_name="Property Mismatch", describe both properties
- Deduplicate observations
- Use higher severity if sources differ
- Never invent information
- Write "Not Available" for missing info

INSPECTION:
{inspection_json}

THERMAL:
{thermal_json}
"""


def merge_findings(inspection: InspectionData, thermal: ThermalData) -> MergedData:
    logger.info("Starting merge...")

    inspection_summary = {
        "property_name": inspection.property_name,
        "property_address": inspection.property_address,
        "inspection_date": inspection.inspection_date,
        "areas": [
            {"area_name": a.area_name, "observations": a.observations[:3], "severity": a.severity}
            for a in inspection.areas[:8]
        ],
        "missing_info": inspection.missing_info[:3],
    }

    thermal_summary = {
        "property_name": getattr(thermal, 'property_name', 'Not Available'),
        "client_name": getattr(thermal, 'property_name', 'Not Available'),
        "scan_date": thermal.scan_date,
        "equipment_used": thermal.equipment_used,
        "findings": [
            {"area_name": f.area_name, "temperature_max": f.temperature_max, "anomalies": f.anomalies[:3]}
            for f in thermal.findings[:8]
        ],
        "missing_info": thermal.missing_info[:3],
    }

    prompt = MERGE_PROMPT.format(
        inspection_json=_truncate_json(inspection_summary),
        thermal_json=_truncate_json(thermal_summary),
    )
    logger.info(f"Merge prompt: {len(prompt)} chars")

    try:
        response = client.chat.completions.create(
            model=settings.groq_model_merge,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=3000,
        )
        raw = response.choices[0].message.content.strip()
        logger.info(f"Merge response: {len(raw)} chars")

        if not raw:
            raise ValueError("Empty response from Groq merger")

        if "```" in raw:
            for part in raw.split("```"):
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                try:
                    data = json.loads(part)
                    return _build_merged(data, inspection, thermal)
                except Exception:
                    continue

        data = json.loads(raw)
        return _build_merged(data, inspection, thermal)

    except json.JSONDecodeError as e:
        logger.error(f"Merge JSON parse error: {e}")
        raise
    except Exception as e:
        logger.error(f"Merge failed: {e}")
        raise


def _build_merged(data: dict, inspection: InspectionData, thermal: ThermalData) -> MergedData:
    merged = MergedData(**data)

    # Re-attach images
    insp_img_map = {a.area_name.lower(): a.images for a in inspection.areas}
    thermal_img_map = {f.area_name.lower(): f.images for f in thermal.findings}

    for area in merged.areas:
        key = area.area_name.lower()
        area.images = insp_img_map.get(key, []) + thermal_img_map.get(key, [])
        if not area.images:
            for k, imgs in {**insp_img_map, **thermal_img_map}.items():
                if k in key or key in k:
                    area.images += imgs

    logger.info(f"Merge complete: {len(merged.areas)} areas, {len(merged.conflicts)} conflicts")
    return merged