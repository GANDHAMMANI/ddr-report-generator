from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class SeverityLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"
    SEVERE = "Severe"       # HSB thermal reports use this
    ALERT = "Alert"         # HSB thermal reports use this
    ADVISORY = "Advisory"   # HSB thermal reports use this
    NOT_AVAILABLE = "Not Available"


# ─── Image Model ──────────────────────────────────────────────────────────────

class ImageData(BaseModel):
    image_id: str
    base64_data: str                        # Base64 encoded image
    format: str = "jpeg"                    # jpeg or png
    source: str                             # "inspection" or "thermal"
    page_number: Optional[int] = None
    caption: Optional[str] = None
    area_name: Optional[str] = None         # Mapped area after processing


# ─── Stage 1: Raw Extracted Data ──────────────────────────────────────────────

class RawDocument(BaseModel):
    source: str                             # "inspection" or "thermal"
    markdown_content: str                   # Full markdown from OpenDataLoader
    images: List[ImageData] = []
    page_count: int = 0


# ─── Stage 2: Structured Extraction ──────────────────────────────────────────

class AreaObservation(BaseModel):
    area_name: str
    observations: List[str] = []
    severity: SeverityLevel = SeverityLevel.NOT_AVAILABLE
    images: List[ImageData] = []


class InspectionData(BaseModel):
    property_name: Optional[str] = "Not Available"
    inspection_date: Optional[str] = "Not Available"
    inspector_name: Optional[str] = "Not Available"
    property_address: Optional[str] = "Not Available"
    areas: List[AreaObservation] = []
    general_observations: List[str] = []
    missing_info: List[str] = []


class ThermalFinding(BaseModel):
    area_name: str
    temperature_min: Optional[str] = "Not Available"
    temperature_max: Optional[str] = "Not Available"
    temperature_delta: Optional[str] = "Not Available"
    anomalies: List[str] = []
    images: List[ImageData] = []


class ThermalData(BaseModel):
    scan_date: Optional[str] = "Not Available"
    equipment_used: Optional[str] = "Not Available"
    findings: List[ThermalFinding] = []
    general_notes: List[str] = []
    missing_info: List[str] = []


# ─── Stage 3: Merged Data ─────────────────────────────────────────────────────

class ConflictItem(BaseModel):
    area_name: str
    inspection_says: str
    thermal_says: str
    conflict_description: str


class MergedAreaFinding(BaseModel):
    area_name: str
    inspection_observations: List[str] = []
    thermal_observations: List[str] = []
    combined_summary: str = ""
    severity: SeverityLevel = SeverityLevel.NOT_AVAILABLE
    severity_reasoning: str = ""
    probable_root_cause: str = "Not Available"
    recommended_actions: List[str] = []
    images: List[ImageData] = []
    has_conflict: bool = False


class MergedData(BaseModel):
    property_name: str = "Not Available"
    property_address: str = "Not Available"
    inspection_date: str = "Not Available"
    areas: List[MergedAreaFinding] = []
    conflicts: List[ConflictItem] = []
    global_missing: List[str] = []


# ─── Stage 4: Final DDR Report ────────────────────────────────────────────────

class SeverityItem(BaseModel):
    area_name: str
    severity: SeverityLevel
    reasoning: str


class ActionItem(BaseModel):
    area_name: str
    priority: str                           # "Immediate" / "Short-term" / "Long-term"
    action: str
    timeline: str


class AreaSection(BaseModel):
    area_name: str
    observations: List[str] = []
    thermal_findings: List[str] = []
    images: List[ImageData] = []
    has_conflict: bool = False
    conflict_note: Optional[str] = None


class DDRReport(BaseModel):
    report_id: str
    generated_at: str
    property_name: str = "Not Available"
    property_address: str = "Not Available"
    inspection_date: str = "Not Available"

    # 7 Sections
    section_1_summary: str = ""
    section_2_area_wise: List[AreaSection] = []
    section_3_root_cause: str = ""
    section_4_severity: List[SeverityItem] = []
    section_5_actions: List[ActionItem] = []
    section_6_notes: str = ""
    section_7_missing: List[str] = []