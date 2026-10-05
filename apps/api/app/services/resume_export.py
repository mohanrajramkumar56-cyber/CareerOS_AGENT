"""
CareerOS Resume Export — PDF and DOCX generation.

PDF: markdown → HTML → PDF via weasyprint
DOCX: structured data → python-docx

All exports use only verified candidate evidence (truth policy enforced upstream).
"""
from __future__ import annotations

import io
import re
from typing import Optional


def markdown_to_pdf(markdown_content: str, title: str = "Resume") -> bytes:
    """
    Convert markdown resume to PDF bytes.
    Uses weasyprint for HTML→PDF conversion.
    Falls back gracefully if weasyprint unavailable.
    """
    try:
        import markdown as md
        from weasyprint import CSS, HTML
    except ImportError:
        raise ImportError("PDF export requires: pip install markdown weasyprint")

    # Convert markdown to HTML
    html_body = md.markdown(
        markdown_content,
        extensions=["tables", "fenced_code"],
    )

    # Wrap in a styled HTML document
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11pt;
                   line-height: 1.5; margin: 0; padding: 0; color: #1a1a1a; }}
            .page {{ max-width: 780px; margin: 0 auto; padding: 40px 50px; }}
            h1 {{ font-size: 22pt; margin-bottom: 4px; color: #111; border-bottom: 2px solid #333; padding-bottom: 6px; }}
            h2 {{ font-size: 13pt; margin-top: 20px; margin-bottom: 6px; color: #222;
                  border-bottom: 1px solid #ccc; padding-bottom: 3px; text-transform: uppercase; letter-spacing: 0.5px; }}
            h3 {{ font-size: 11pt; margin-top: 12px; margin-bottom: 2px; color: #333; }}
            p {{ margin: 4px 0; }}
            ul {{ margin: 4px 0; padding-left: 18px; }}
            li {{ margin: 2px 0; }}
            strong {{ color: #111; }}
            @page {{ margin: 20mm 15mm; size: A4; }}
        </style>
    </head>
    <body><div class="page">{html_body}</div></body>
    </html>
    """

    pdf_bytes = HTML(string=html).write_pdf(
        stylesheets=[CSS(string="@page { margin: 20mm 15mm; }")]
    )
    return pdf_bytes


def markdown_to_docx(markdown_content: str, title: str = "Resume") -> bytes:
    """
    Convert markdown resume to DOCX bytes.
    Uses python-docx to produce an ATS-friendly Word document.
    """
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Inches, Pt, RGBColor
    except ImportError:
        raise ImportError("DOCX export requires: pip install python-docx")

    doc = Document()

    # Page margins
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    section = doc.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

    lines = markdown_content.strip().split("\n")

    for line in lines:
        line = line.rstrip()

        if line.startswith("# "):
            p = doc.add_heading(line[2:], level=1)
            p.runs[0].font.size = Pt(18)
        elif line.startswith("## "):
            p = doc.add_heading(line[3:], level=2)
            p.runs[0].font.size = Pt(13)
        elif line.startswith("### "):
            p = doc.add_heading(line[4:], level=3)
            p.runs[0].font.size = Pt(11)
        elif line.startswith("- ") or line.startswith("* "):
            doc.add_paragraph(line[2:], style="List Bullet")
        elif line.strip() == "" or line.strip() == "---":
            if line.strip() == "---":
                doc.add_paragraph()
        else:
            # Handle **bold** inline
            para = doc.add_paragraph()
            parts = re.split(r"(\*\*[^*]+\*\*)", line)
            for part in parts:
                if part.startswith("**") and part.endswith("**"):
                    run = para.add_run(part[2:-2])
                    run.bold = True
                else:
                    para.add_run(part)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
