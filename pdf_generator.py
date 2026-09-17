import io
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_pdf(scan_data, upload_folder="uploads"):
    buffer = io.BytesIO()
    # letter is 612 x 792 points. Margins: 36 points (0.5 inch). Printable width: 540 points.
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter, 
        rightMargin=36, 
        leftMargin=36, 
        topMargin=36, 
        bottomMargin=36
    )
    story = []
    
    styles = getSampleStyleSheet()
    
    # Custom text styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=colors.HexColor('#1E3A8A'), # Deep Blue
        spaceAfter=5
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        textColor=colors.HexColor('#475569'),
        spaceAfter=15
    )
    
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=12,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )
    
    bold_style = ParagraphStyle(
        'Bold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    # Colors based on compliance status
    status = scan_data.get("overall_status", "Unknown")
    status_colors = {
        "PASSED": colors.HexColor('#10B981'),  # Emerald Green
        "PASS": colors.HexColor('#10B981'),
        "WARNING": colors.HexColor('#D97706'), # Amber
        "PARTIAL": colors.HexColor('#D97706'),
        "FAILED": colors.HexColor('#EF4444'),   # Rose Red
        "FAIL": colors.HexColor('#EF4444')
    }
    status_color = status_colors.get(status.upper(), colors.HexColor('#64748B'))
    
    # Report Header
    story.append(Paragraph("LEGAL METROLOGY COMPLIANCE AUDIT REPORT", title_style))
    story.append(Paragraph("Department of Consumer Affairs (DoCA) • Legal Metrology (Packaged Commodities) Rules, 2011", subtitle_style))
    story.append(Spacer(1, 5))
    
    # Info Section
    info_data = [
        [
            Paragraph("<b>Report ID:</b>", bold_style), Paragraph(scan_data.get("id", ""), body_style),
            Paragraph("<b>Inspection Date:</b>", bold_style), Paragraph(scan_data.get("timestamp", "")[:19].replace("T", " "), body_style)
        ],
        [
            Paragraph("<b>Commodity / Brand:</b>", bold_style), Paragraph(scan_data.get("product_name", "Unknown Product"), body_style),
            Paragraph("<b>Source Filename:</b>", bold_style), Paragraph(scan_data.get("filename", ""), body_style)
        ],
        [
            Paragraph("<b>Compliance Score:</b>", bold_style), Paragraph(f"<b>{scan_data.get('compliance_score', 0)}%</b>", body_style),
            Paragraph("<b>Audit Status:</b>", bold_style), Paragraph(f"<font color='{status_color}'><b>{status.upper()}</b></font>", body_style)
        ]
    ]
    
    info_table = Table(info_data, colWidths=[110, 160, 110, 160])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 15))
    
    # Scanned Evidence Block
    img_filename = scan_data.get("filename", "")
    img_path = os.path.join(upload_folder, img_filename)
    if img_filename and os.path.exists(img_path):
        try:
            from PIL import Image as PILImage
            # Test-open the image to verify it's a valid format before reportlab lazy-loads it
            with PILImage.open(img_path) as test_img:
                test_img.verify()
                
            # Restrict image sizes to prevent overflow
            rl_img = RLImage(img_path, width=120, height=90)
            rl_img.hAlign = 'LEFT'
            story.append(Paragraph("<b>Scanned Image Evidence:</b>", h2_style))
            story.append(rl_img)
            story.append(Spacer(1, 10))
        except Exception as e:
            print(f"[PDF Gen Warning] Skipping invalid image file: {e}")
            
    # Audit Findings Section
    story.append(Paragraph("Detailed Compliance Audit Checklist", h2_style))
    
    findings_data = [[
        Paragraph("<b>Declaration Checklist Item</b>", bold_style),
        Paragraph("<b>Detected Value</b>", bold_style),
        Paragraph("<b>Status</b>", bold_style),
        Paragraph("<b>Assessment & Regulatory Remarks</b>", bold_style)
    ]]
    
    results = scan_data.get("results", {})
    for key, res in results.items():
        res_status = res.get("status", "Failed").upper()
        res_color = status_colors.get(res_status, colors.HexColor('#64748B'))
        
        # Format the description & clause references nicely
        friendly_name = res.get("friendly_name", key)
        detected_val = res.get("detected_value") or "Not detected"
        clause_ref = res.get("clause")
        ref_text = f"<br/><font size='7' color='#475569'><b>Reference:</b> {clause_ref}</font>" if clause_ref else ""
        
        # Ensure detected_val is HTML safe for Paragraph
        detected_val_safe = detected_val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        findings_data.append([
            Paragraph(friendly_name, body_style),
            Paragraph(detected_val_safe, body_style),
            Paragraph(f"<font color='{res_color}'><b>{res_status}</b></font>", body_style),
            Paragraph(f"{res.get('message')}{ref_text}", body_style)
        ])
        
    findings_table = Table(findings_data, colWidths=[120, 110, 60, 250])
    findings_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    
    story.append(findings_table)
    story.append(Spacer(1, 10))
    
    # Raw OCR text segment
    story.append(Paragraph("Extracted Raw OCR Stream", h2_style))
    raw_text = scan_data.get("extracted_text", "No text available.")
    # Sanitize and convert newlines to HTML break tags
    raw_text_sanitized = raw_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
    
    raw_ocr_style = ParagraphStyle(
        'RawOCRText',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        backColor=colors.HexColor('#F1F5F9'),
        borderColor=colors.HexColor('#E2E8F0'),
        borderWidth=0.5,
        borderPadding=6,
        spaceAfter=15
    )
    story.append(Paragraph(raw_text_sanitized, raw_ocr_style))
    
    # Official Signatures
    story.append(Spacer(1, 10))
    sign_data = [
        [Paragraph("<b>Audit System Inspector Signature:</b>", body_style), Paragraph("<b>Official Department Stamp:</b>", body_style)],
        [Paragraph("<br/><br/>_______________________________________", body_style), Paragraph("<br/><br/>_______________________________________", body_style)],
        [Paragraph("Legal Metrology Enforcement System (LMES)", body_style), Paragraph("DoCA Inspection Division, Government of India", body_style)]
    ]
    sign_table = Table(sign_data, colWidths=[270, 270])
    sign_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(sign_table)
    
    # Automated Legal Verification Footer
    story.append(Spacer(1, 15))
    story.append(Paragraph("<font size='7.5' color='#64748B'><i>Automated Legal Verification via LMES Engine v2.4</i></font>", body_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
