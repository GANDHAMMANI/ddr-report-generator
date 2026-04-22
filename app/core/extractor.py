import json
from groq import Groq
from app.config import settings
from app.models.pipeline import RawDocument, InspectionData, ThermalData
from app.utils.logger import logger

client = Groq(api_key=settings.groq_api_key)
MAX_CONTEXT_CHARS = 6000


def _parse_json(raw: str) -> dict:
    """Parse JSON from LLM response, handling code fences."""
    raw = raw.strip()
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip().lstrip("json").strip()
            try:
                return json.loads(part)
            except Exception:
                continue
    return json.loads(raw)


def _call_groq(prompt: str, label: str, max_tokens: int = 2048) -> dict:
    """Call Groq with automatic retry on empty response."""
    logger.info(f"Groq [{settings.groq_model_extract}] → {label} | {len(prompt)} chars")

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=settings.groq_model_extract,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=max_tokens,
            )
            raw = response.choices[0].message.content.strip()

            if not raw:
                logger.warning(f"Empty response attempt {attempt+1} for {label}")
                # Reduce prompt on retry
                if attempt < 2:
                    prompt = prompt[:int(len(prompt) * 0.7)]
                    logger.info(f"Retrying with {len(prompt)} chars")
                continue

            return _parse_json(raw)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error attempt {attempt+1} in {label}: {e}")
            if attempt == 2:
                raise
        except Exception as e:
            logger.error(f"Groq error attempt {attempt+1} in {label}: {e}")
            if attempt == 2:
                raise

    raise ValueError(f"All 3 attempts failed for {label}")


def _get_context(doc: RawDocument, queries: list, source: str) -> str:
    """Get relevant context using ChromaDB RAG with fallback to truncation."""
    try:
        from app.core.rag_retriever import DocumentRAG
        rag = DocumentRAG(collection_name=source)
        rag.index_document(doc.markdown_content, source)
        context = rag.retrieve_multi(queries, n_per_query=5, source_filter=source)
        if len(context) > MAX_CONTEXT_CHARS:
            context = context[:MAX_CONTEXT_CHARS]
        logger.info(f"RAG context for {source}: {len(context)} chars")
        return context
    except Exception as e:
        logger.warning(f"RAG failed ({e}) — using truncation fallback")
        text = doc.markdown_content
        half = MAX_CONTEXT_CHARS // 2
        return text[:half] + "\n...[truncated]...\n" + text[-half:]


INSPECTION_QUERIES = [
    "property name client owner inspector",
    "property address location street city",
    "inspection date",
    "area observations defects issues",
    "severity critical high medium low",
    "missing information not available",
]

THERMAL_QUERIES = [
    "client XYC corporation who ordered inspection",
    "client name company",
    "property location facility ABC company",
    "property address street city",
    "service date scan date",
    "equipment FLIR thermographer",
    "critical severe alert advisory",
    "temperature max min rise",
    "area switchyard transformer breaker",
    "repair cost recommendation",
    "FPE stab-lok overheating",
]

INSPECTION_PROMPT = """You are a building inspection analyst.
Extract all information from the report below.
Return ONLY valid JSON:
{{
  "property_name": "exact client/owner name or Not Available",
  "inspection_date": "string or Not Available",
  "inspector_name": "string or Not Available",
  "property_address": "full address or Not Available",
  "areas": [
    {{
      "area_name": "string",
      "observations": ["list"],
      "severity": "Low | Medium | High | Critical | Not Available",
      "page_numbers": [integers]
    }}
  ],
  "general_observations": ["list"],
  "missing_info": ["list"]
}}
Rules: Extract EXACT names. Include page_numbers. No invented info. Not Available for missing.

REPORT:
{content}"""


THERMAL_PROMPT = """You are a thermal imaging analyst.
Extract all information from the report below.
Return ONLY valid JSON:
{{
  "client_name": "who ordered the inspection e.g. XYC Corporation",
  "property_name": "facility/location name e.g. ABC Company Inc",
  "property_address": "full address or Not Available",
  "scan_date": "string or Not Available",
  "equipment_used": "string or Not Available",
  "findings": [
    {{
      "area_name": "string",
      "severity": "Critical | Severe | Alert | Advisory | Not Available",
      "temperature_max": "string or Not Available",
      "temperature_delta": "string or Not Available",
      "anomalies": ["list"],
      "page_numbers": [integers]
    }}
  ],
  "general_notes": ["list"],
  "missing_info": ["list"]
}}
Rules: Extract EXACT client name. Include all findings. page_numbers required. Not Available for missing.

REPORT:
{content}"""


def extract_inspection_data(doc: RawDocument) -> InspectionData:
    context = _get_context(doc, INSPECTION_QUERIES, "inspection")
    data = _call_groq(INSPECTION_PROMPT.format(content=context), "inspection")
    inspection = InspectionData(**{k: v for k, v in data.items()
                                   if k in InspectionData.model_fields})
    for area in inspection.areas:
        area_raw = next((a for a in data.get("areas", [])
                        if a.get("area_name") == area.area_name), {})
        pages = area_raw.get("page_numbers", [])
        area.images = [img for img in doc.images
                      if img.source == "inspection" and img.page_number in pages]
        logger.info(f"  Inspection '{area.area_name}': pages={pages} imgs={len(area.images)}")
    logger.info(f"Inspection: {len(inspection.areas)} areas extracted")
    return inspection


def extract_thermal_data(doc: RawDocument) -> ThermalData:
    context = _get_context(doc, THERMAL_QUERIES, "thermal")
    data = _call_groq(THERMAL_PROMPT.format(content=context), "thermal")

    # Use client_name as primary property name
    client = data.pop("client_name", None)
    location = data.get("property_name", "Not Available")
    if client and client != "Not Available":
        if location and location != "Not Available":
            data["property_name"] = f"{client} ({location})"
        else:
            data["property_name"] = client

    thermal = ThermalData(**{k: v for k, v in data.items()
                             if k in ThermalData.model_fields})
    for finding in thermal.findings:
        finding_raw = next((f for f in data.get("findings", [])
                           if f.get("area_name") == finding.area_name), {})
        pages = finding_raw.get("page_numbers", [])
        finding.images = [img for img in doc.images
                         if img.source == "thermal" and img.page_number in pages]
        logger.info(f"  Thermal '{finding.area_name}': pages={pages} imgs={len(finding.images)}")
    logger.info(f"Thermal: {len(thermal.findings)} findings extracted")
    return thermal