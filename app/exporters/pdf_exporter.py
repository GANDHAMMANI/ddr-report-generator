from pathlib import Path
from app.models.pipeline import DDRReport
from app.exporters.html_exporter import export_html
from app.utils.logger import logger


def export_pdf(ddr: DDRReport, output_dir: Path) -> Path:
    """Export DDR as PDF. Tries pdfkit → reportlab as fallback."""
    logger.info("Exporting DDR to PDF...")

    html_path = export_html(ddr, output_dir)
    output_path = output_dir / "ddr_report.pdf"

    # ── Try pdfkit (wkhtmltopdf) ──────────────────────────────────────────────
    try:
        import pdfkit
        options = {
            'page-size': 'A4',
            'margin-top': '15mm',
            'margin-right': '15mm',
            'margin-bottom': '15mm',
            'margin-left': '15mm',
            'encoding': 'UTF-8',
            'enable-local-file-access': None,
            'quiet': None,
        }
        pdfkit.from_file(str(html_path), str(output_path), options=options)
        logger.info(f"PDF exported via pdfkit → {output_path}")
        return output_path
    except Exception as e:
        logger.warning(f"pdfkit failed: {e}, trying reportlab...")

    # ── Fallback: reportlab ───────────────────────────────────────────────────
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

        doc = SimpleDocTemplate(
            str(output_path), pagesize=A4,
            leftMargin=2*cm, rightMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm
        )
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle('T', parent=styles['Title'],
            textColor=colors.HexColor('#1E3A5F'), fontSize=20, spaceAfter=6)
        h2_style = ParagraphStyle('H2', parent=styles['Heading2'],
            textColor=colors.HexColor('#1E3A5F'), fontSize=14, spaceBefore=14, spaceAfter=6)
        body_style = ParagraphStyle('B', parent=styles['Normal'],
            fontSize=11, leading=16, spaceAfter=6, alignment=4)  # 4=JUSTIFY
        bullet_style = ParagraphStyle('BL', parent=styles['Normal'],
            fontSize=11, leading=16, leftIndent=20, spaceAfter=4)

        # Title
        story.append(Paragraph("Detailed Diagnostic Report (DDR)", title_style))
        story.append(Paragraph("AI-Generated Professional Property Assessment", 
            ParagraphStyle('Sub', parent=styles['Normal'], 
                textColor=colors.HexColor('#6B7280'), fontSize=11, italic=True, spaceAfter=12)))
        story.append(HRFlowable(width="100%", color=colors.HexColor('#1E3A5F')))
        story.append(Spacer(1, 12))

        # Property info
        story.append(Paragraph(f"<b>Property:</b> {ddr.property_name}", body_style))
        story.append(Paragraph(f"<b>Address:</b> {ddr.property_address}", body_style))
        story.append(Paragraph(f"<b>Inspection Date:</b> {ddr.inspection_date}", body_style))
        story.append(Paragraph(f"<b>Report Generated:</b> {ddr.generated_at}", body_style))
        story.append(Spacer(1, 12))

        # Section 1
        story.append(HRFlowable(width="100%", color=colors.HexColor('#E5E7EB')))
        story.append(Paragraph("1. Property Issue Summary", h2_style))
        story.append(Paragraph(ddr.section_1_summary or "Not Available", body_style))

        # Section 2
        story.append(HRFlowable(width="100%", color=colors.HexColor('#E5E7EB')))
        story.append(Paragraph("2. Area-wise Observations", h2_style))
        for area in ddr.section_2_area_wise:
            story.append(Paragraph(f"<b>📍 {area.area_name}</b>", 
                ParagraphStyle('AH', parent=styles['Normal'], fontSize=12, 
                    textColor=colors.HexColor('#1E3A5F'), spaceBefore=8, spaceAfter=4)))
            for obs in area.observations:
                story.append(Paragraph(f"• {obs}", bullet_style))
            for tf in area.thermal_findings:
                story.append(Paragraph(f"🌡️ {tf}", 
                    ParagraphStyle('TF', parent=styles['Normal'], fontSize=11,
                        leftIndent=20, textColor=colors.HexColor('#1E40AF'), spaceAfter=4)))
            if area.has_conflict and area.conflict_note:
                story.append(Paragraph(f"⚠️ Conflict: {area.conflict_note}",
                    ParagraphStyle('CF', parent=styles['Normal'], fontSize=10,
                        textColor=colors.HexColor('#F59E0B'), leftIndent=20, spaceAfter=4)))
            # Add max 2 images per area
            img_count = 0
            for img in area.images[:2]:
                try:
                    import base64, io
                    from reportlab.platypus import Image as RLImage
                    img_bytes = base64.b64decode(img.base64_data)
                    img_stream = io.BytesIO(img_bytes)
                    rl_img = RLImage(img_stream, width=4*cm*1.5, height=3*cm*1.5)
                    story.append(rl_img)
                    caption_text = img.caption or f"{img.source.title()} Image"
                    story.append(Paragraph(caption_text,
                        ParagraphStyle('IC', parent=styles['Normal'],
                            fontSize=8, textColor=colors.HexColor('#6B7280'),
                            alignment=1, spaceAfter=6)))
                    img_count += 1
                except Exception as ie:
                    story.append(Paragraph("⚠ Image Not Available",
                        ParagraphStyle('IN', parent=styles['Normal'],
                            fontSize=9, textColor=colors.HexColor('#9CA3AF'),
                            leftIndent=20, spaceAfter=4)))
            if img_count == 0 and not area.images:
                story.append(Paragraph("📷 Image Not Available",
                    ParagraphStyle('IN2', parent=styles['Normal'],
                        fontSize=9, textColor=colors.HexColor('#9CA3AF'),
                        leftIndent=20, spaceAfter=4)))

        # Section 3
        story.append(HRFlowable(width="100%", color=colors.HexColor('#E5E7EB')))
        story.append(Paragraph("3. Probable Root Cause", h2_style))
        story.append(Paragraph(ddr.section_3_root_cause or "Not Available", body_style))

        # Section 4
        story.append(HRFlowable(width="100%", color=colors.HexColor('#E5E7EB')))
        story.append(Paragraph("4. Severity Assessment", h2_style))
        sev_colors = {"Critical": "#DC2626", "High": "#EA580C", 
                      "Medium": "#D97706", "Low": "#16A34A", "Not Available": "#6B7280"}
        for item in ddr.section_4_severity:
            clr = sev_colors.get(item.severity, "#6B7280")
            story.append(Paragraph(
                f'<font color="{clr}"><b>[{item.severity.upper()}]</b></font> '
                f'<b>{item.area_name}:</b> {item.reasoning}', body_style))

        # Section 5
        story.append(HRFlowable(width="100%", color=colors.HexColor('#E5E7EB')))
        story.append(Paragraph("5. Recommended Actions", h2_style))
        pri_colors = {"Immediate": "#DC2626", "Short-term": "#D97706", "Long-term": "#2563EB"}
        for action in ddr.section_5_actions:
            clr = pri_colors.get(action.priority, "#6B7280")
            story.append(Paragraph(
                f'<font color="{clr}"><b>[{action.priority.upper()}]</b></font> '
                f'<b>{action.area_name}</b> — {action.action} ({action.timeline})', body_style))

        # Section 6
        story.append(HRFlowable(width="100%", color=colors.HexColor('#E5E7EB')))
        story.append(Paragraph("6. Additional Notes", h2_style))
        story.append(Paragraph(ddr.section_6_notes or "Not Available", body_style))

        # Section 7
        story.append(HRFlowable(width="100%", color=colors.HexColor('#E5E7EB')))
        story.append(Paragraph("7. Missing or Unclear Information", h2_style))
        if ddr.section_7_missing:
            for item in ddr.section_7_missing:
                story.append(Paragraph(f"• {item}", bullet_style))
        else:
            story.append(Paragraph("No missing information identified.", body_style))

        # Footer
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", color=colors.HexColor('#E5E7EB')))
        story.append(Paragraph(
            f"Report ID: {ddr.report_id}  |  Generated: {ddr.generated_at}",
            ParagraphStyle('Footer', parent=styles['Normal'],
                fontSize=9, textColor=colors.HexColor('#9CA3AF'), alignment=1, spaceBefore=8)))

        doc.build(story)
        logger.info(f"PDF exported via reportlab → {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"All PDF export methods failed: {e}")
        raise RuntimeError(f"PDF export failed: {e}")