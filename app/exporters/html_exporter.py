from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.models.pipeline import DDRReport
from app.core.image_handler import get_severity_color, get_priority_color
from app.utils.logger import logger

# Inline HTML template as fallback (also used directly)
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>DDR Report - {{ report.property_name }}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', Arial, sans-serif; color: #1f2937; background: #f9fafb; }
  .container { max-width: 960px; margin: 0 auto; padding: 40px 24px; }
  
  /* Header */
  .report-header { background: #1e3a5f; color: white; padding: 40px; border-radius: 12px; margin-bottom: 32px; }
  .report-header h1 { font-size: 28px; margin-bottom: 8px; }
  .report-header .meta { font-size: 14px; opacity: 0.85; margin-top: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .report-header .meta span { display: block; }
  .report-header .meta strong { color: #93c5fd; }

  /* Sections */
  .section { background: white; border-radius: 12px; padding: 32px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  .section-title { font-size: 20px; font-weight: 700; color: #1e3a5f; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid #e5e7eb; display: flex; align-items: center; gap: 10px; }
  .section-number { background: #1e3a5f; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; flex-shrink: 0; }

  /* Summary */
  .summary-text { line-height: 1.8; color: #374151; font-size: 15px; text-align: justify; }

  /* Area Cards */
  .area-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
  .area-card.has-conflict { border-color: #f59e0b; background: #fffbeb; }
  .area-name { font-size: 17px; font-weight: 600; color: #1e3a5f; margin-bottom: 12px; }
  .obs-list { list-style: none; padding: 0; }
  .obs-list li { padding: 6px 0 6px 20px; position: relative; font-size: 14px; color: #374151; line-height: 1.6; text-align: justify; }
  .obs-list li::before { content: "•"; position: absolute; left: 0; color: #1e3a5f; font-weight: bold; }
  .thermal-badge { display: inline-block; background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; margin-bottom: 8px; }
  .conflict-note { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 10px 14px; border-radius: 0 6px 6px 0; margin-top: 12px; font-size: 13px; color: #92400e; }

  /* Images */
  .images-grid { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 16px; }
  .report-image { text-align: center; }
  .report-image img { max-width: 280px; max-height: 200px; object-fit: cover; border: 1px solid #e5e7eb; border-radius: 6px; }
  .report-image figcaption { font-size: 11px; color: #6b7280; margin-top: 4px; }
  .image-missing { color: #9ca3af; font-style: italic; font-size: 13px; padding: 8px; border: 1px dashed #d1d5db; border-radius: 4px; }

  /* Severity */
  .severity-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; color: white; }
  .severity-grid { display: grid; gap: 12px; }
  .severity-row { display: flex; align-items: flex-start; gap: 16px; padding: 14px; border: 1px solid #e5e7eb; border-radius: 8px; }
  .severity-info { flex: 1; }
  .severity-area { font-weight: 600; color: #1f2937; margin-bottom: 4px; }
  .severity-reasoning { font-size: 13px; color: #6b7280; line-height: 1.5; }

  /* Actions */
  .action-item { display: flex; gap: 16px; padding: 14px; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 10px; align-items: flex-start; }
  .priority-badge { padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 700; color: white; white-space: nowrap; flex-shrink: 0; }
  .action-content { flex: 1; }
  .action-area { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
  .action-text { font-size: 14px; color: #1f2937; line-height: 1.5; }
  .action-timeline { font-size: 12px; color: #2563eb; margin-top: 4px; font-weight: 500; }

  /* Missing Info */
  .missing-list { list-style: none; padding: 0; }
  .missing-list li { padding: 8px 12px; background: #f9fafb; border-left: 3px solid #9ca3af; margin-bottom: 6px; border-radius: 0 4px 4px 0; font-size: 14px; color: #374151; }

  /* Root cause & notes */
  .prose { line-height: 1.8; color: #374151; font-size: 15px; text-align: justify; }

  /* Footer */
  .footer { text-align: center; padding: 24px; color: #9ca3af; font-size: 13px; }
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div class="report-header">
    <h1>Detailed Diagnostic Report (DDR)</h1>
    <p style="opacity:0.75; margin-top:4px;">AI-Generated Professional Property Assessment</p>
    <div class="meta">
      <span><strong>Property:</strong> {{ report.property_name }}</span>
      <span><strong>Address:</strong> {{ report.property_address }}</span>
      <span><strong>Inspection Date:</strong> {{ report.inspection_date }}</span>
      <span><strong>Report Generated:</strong> {{ report.generated_at }}</span>
    </div>
  </div>

  <!-- Section 1 -->
  <div class="section">
    <div class="section-title"><div class="section-number">1</div> Property Issue Summary</div>
    <p class="summary-text">{{ report.section_1_summary }}</p>
  </div>

  <!-- Section 2 -->
  <div class="section">
    <div class="section-title"><div class="section-number">2</div> Area-wise Observations</div>
    {% for area in report.section_2_area_wise %}
    <div class="area-card {% if area.has_conflict %}has-conflict{% endif %}">
      <div class="area-name">📍 {{ area.area_name }}</div>
      
      {% if area.observations %}
      <p style="font-size:13px; font-weight:600; color:#6b7280; margin-bottom:6px;">VISUAL INSPECTION</p>
      <ul class="obs-list">
        {% for obs in area.observations %}<li>{{ obs }}</li>{% endfor %}
      </ul>
      {% endif %}

      {% if area.thermal_findings %}
      <div style="margin-top:12px;">
        <span class="thermal-badge">🌡️ THERMAL FINDINGS</span>
        <ul class="obs-list">
          {% for tf in area.thermal_findings %}<li>{{ tf }}</li>{% endfor %}
        </ul>
      </div>
      {% endif %}

      {% if area.has_conflict and area.conflict_note %}
      <div class="conflict-note">⚠️ <strong>Conflict Detected:</strong> {{ area.conflict_note }}</div>
      {% endif %}

      {% if area.images %}
      <div class="images-grid">
        {% for img in area.images %}
        <figure class="report-image">
          <img src="data:image/{{ img.format }};base64,{{ img.base64_data }}" alt="{{ img.caption or 'Inspection Image' }}"/>
          <figcaption>{{ img.caption or (img.source|title + ' Image') }}</figcaption>
        </figure>
        {% endfor %}
      </div>
      {% else %}
      <p class="image-missing" style="margin-top:12px;">📷 Image Not Available for this area</p>
      {% endif %}
    </div>
    {% endfor %}
  </div>

  <!-- Section 3 -->
  <div class="section">
    <div class="section-title"><div class="section-number">3</div> Probable Root Cause</div>
    <p class="prose">{{ report.section_3_root_cause }}</p>
  </div>

  <!-- Section 4 -->
  <div class="section">
    <div class="section-title"><div class="section-number">4</div> Severity Assessment</div>
    <div class="severity-grid">
      {% for item in report.section_4_severity %}
      <div class="severity-row">
        <span class="severity-badge" style="background:{{ severity_color(item.severity) }}">{{ item.severity }}</span>
        <div class="severity-info">
          <div class="severity-area">{{ item.area_name }}</div>
          <div class="severity-reasoning">{{ item.reasoning }}</div>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>

  <!-- Section 5 -->
  <div class="section">
    <div class="section-title"><div class="section-number">5</div> Recommended Actions</div>
    {% for action in report.section_5_actions %}
    <div class="action-item">
      <span class="priority-badge" style="background:{{ priority_color(action.priority) }}">{{ action.priority }}</span>
      <div class="action-content">
        <div class="action-area">{{ action.area_name }}</div>
        <div class="action-text">{{ action.action }}</div>
        <div class="action-timeline">🕐 {{ action.timeline }}</div>
      </div>
    </div>
    {% endfor %}
  </div>

  <!-- Section 6 -->
  <div class="section">
    <div class="section-title"><div class="section-number">6</div> Additional Notes</div>
    <p class="prose">{{ report.section_6_notes }}</p>
  </div>

  <!-- Section 7 -->
  <div class="section">
    <div class="section-title"><div class="section-number">7</div> Missing or Unclear Information</div>
    {% if report.section_7_missing %}
    <ul class="missing-list">
      {% for item in report.section_7_missing %}<li>{{ item }}</li>{% endfor %}
    </ul>
    {% else %}
    <p style="color:#6b7280; font-style:italic;">No missing information identified.</p>
    {% endif %}
  </div>

  <div class="footer">
    Report ID: {{ report.report_id }} &nbsp;|&nbsp; Generated by DDR Report Generator &nbsp;|&nbsp; {{ report.generated_at }}
  </div>
</div>
</body>
</html>"""


def export_html(ddr: DDRReport, output_dir: Path) -> Path:
    """Render DDR report as HTML file."""
    logger.info("Exporting DDR to HTML...")

    env = Environment(autoescape=select_autoescape(["html"]))
    env.globals["severity_color"] = get_severity_color
    env.globals["priority_color"] = get_priority_color

    template = env.from_string(HTML_TEMPLATE)
    html_content = template.render(report=ddr)

    output_path = output_dir / "ddr_report.html"
    output_path.write_text(html_content, encoding="utf-8")
    logger.info(f"HTML exported → {output_path}")
    return output_path