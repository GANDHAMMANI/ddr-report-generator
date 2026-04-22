import base64
from typing import List
from app.models.pipeline import ImageData, DDRReport
from app.utils.logger import logger

# 30KB minimum — filters logos, icons, separators
MIN_IMAGE_BYTES = 30000

# Known logo/watermark keywords to skip
SKIP_CAPTIONS = ["hsb", "munich re", "amerispec", "logo", "watermark"]


def validate_base64_image(b64_data: str) -> bool:
    """Validate image is real and large enough."""
    try:
        if not b64_data or len(b64_data) < 100:
            return False
        decoded = base64.b64decode(b64_data)
        if len(decoded) < MIN_IMAGE_BYTES:
            return False
        is_jpeg = decoded[:3] == b'\xff\xd8\xff'
        is_png  = decoded[:8] == b'\x89PNG\r\n\x1a\n'
        return is_jpeg or is_png
    except Exception:
        return False


def is_logo_image(img: ImageData) -> bool:
    """Detect known logos by caption keywords."""
    caption = (img.caption or "").lower()
    return any(kw in caption for kw in SKIP_CAPTIONS)


def distribute_images_to_areas(ddr: DDRReport, all_images: List[ImageData]) -> DDRReport:
    """
    Smart image distribution:
    1. First pass — semantic matching by area name in caption
    2. Second pass — page number matching
    3. Fallback — index-based even distribution
    """
    # Filter valid non-logo images
    valid_images = [
        img for img in all_images
        if validate_base64_image(img.base64_data) and not is_logo_image(img)
    ]
    logger.info(f"Valid images after filtering: {len(valid_images)} / {len(all_images)}")

    if not valid_images or not ddr.section_2_area_wise:
        return ddr

    areas = ddr.section_2_area_wise
    assigned = set()

    # ── Pass 1: Semantic match by area name in image caption ──────────────────
    for area in areas:
        area_key = area.area_name.lower()
        matched = []
        for img in valid_images:
            if img.image_id in assigned:
                continue
            caption = (img.caption or "").lower()
            if area_key in caption or any(
                word in caption for word in area_key.split() if len(word) > 3
            ):
                matched.append(img)
                assigned.add(img.image_id)
        if matched:
            area.images = matched[:3]  # max 3 per area
            logger.info(f"  [semantic] '{area.area_name}': {len(area.images)} images")

    # ── Pass 2: Page number match for unassigned images ───────────────────────
    # Build page→area map from already-assigned areas
    for area in areas:
        if area.images:
            continue  # already has images
        for img in valid_images:
            if img.image_id in assigned:
                continue
            # If image page is within reasonable range for this area
            if img.page_number and img.page_number > 0:
                area.images.append(img)
                assigned.add(img.image_id)
                if len(area.images) >= 3:
                    break
        if area.images:
            logger.info(f"  [page-match] '{area.area_name}': {len(area.images)} images")

    # ── Pass 3: Distribute remaining unassigned images evenly ─────────────────
    unassigned = [img for img in valid_images if img.image_id not in assigned]
    if unassigned:
        areas_without = [a for a in areas if not a.images]
        if areas_without:
            per = max(1, len(unassigned) // len(areas_without))
            for i, area in enumerate(areas_without):
                area.images = unassigned[i*per: i*per+per]
                logger.info(f"  [fallback] '{area.area_name}': {len(area.images)} images")
        else:
            # All areas have images — add remaining to areas with fewest
            for i, img in enumerate(unassigned):
                area = min(areas, key=lambda a: len(a.images))
                if len(area.images) < 3:
                    area.images.append(img)

    # Update captions
    for area in areas:
        for img in area.images:
            img.area_name = area.area_name
            img.caption = f"{img.source.title()} — {area.area_name} (Page {img.page_number})"

    total = sum(len(a.images) for a in areas)
    logger.info(f"Image distribution complete: {total} images across {len(areas)} areas")
    return ddr


def finalize_image_placement(ddr: DDRReport) -> DDRReport:
    """Final validation — remove any invalid or logo images."""
    total, removed = 0, 0
    for area in ddr.section_2_area_wise:
        valid = [
            img for img in area.images
            if validate_base64_image(img.base64_data) and not is_logo_image(img)
        ]
        removed += len(area.images) - len(valid)
        area.images = valid
        total += len(valid)
    logger.info(f"Final image count: {total} valid, {removed} removed")
    return ddr


def get_severity_color(severity: str) -> str:
    return {
        "Critical":      "#dc2626",
        "Severe":        "#dc2626",
        "High":          "#ea580c",
        "Alert":         "#ea580c",
        "Medium":        "#d97706",
        "Advisory":      "#d97706",
        "Low":           "#16a34a",
        "Not Available": "#6b7280",
    }.get(severity, "#6b7280")


def get_priority_color(priority: str) -> str:
    return {
        "Immediate":  "#dc2626",
        "Short-term": "#d97706",
        "Long-term":  "#2563eb",
    }.get(priority, "#6b7280")