"""PDF report generation using ReportLab.

Produces a compliance report for an analysis containing:
- product / category
- analysis id, date, user
- applicable rules with PASS/FAIL/REVIEW/NOT_APPLICABLE
- per-rule reason and evidence
- overall status and summary
- explicit limitations (physical quantity not verified from image)
"""

from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import get_settings

_STATUS_COLORS = {
    "PASS": colors.HexColor("#2e7d32"),
    "FAIL": colors.HexColor("#c62828"),
    "REVIEW": colors.HexColor("#ef6c00"),
    "NOT_APPLICABLE": colors.grey,
}


class ReportGenerator:
    """Generates a local PDF compliance report."""

    def __init__(self):
        self.settings = get_settings()
        self.styles = getSampleStyleSheet()
        self.styles.add(
            ParagraphStyle(
                "RuleTitle",
                parent=self.styles["Normal"],
                fontSize=10,
                spaceAfter=2,
                spaceBefore=8,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "Small",
                parent=self.styles["Normal"],
                fontSize=8,
                textColor=colors.grey,
            )
        )

    def generate(self, analysis_data: dict) -> Path:
        """Build the PDF and return the file path.

        analysis_data is a dict produced by the compliance /run endpoint
        (see app/api/analysis.py) containing product, rules, summary, etc.
        """
        self.settings.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = (
            self.settings.REPORT_DIR
            / f"analysis_{analysis_data['analysis_id']}.pdf"
        )

        doc = SimpleDocTemplate(
            str(report_path),
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
        )

        story = []
        story.append(Paragraph("Packaged Commodities Compliance Report", self.styles["Title"]))
        story.append(Spacer(1, 6))

        # Header info
        meta = Table(
            [
                ["Analysis ID", analysis_data.get("analysis_id", "")],
                ["Product", analysis_data.get("product", {}).get("name", "")],
                ["Category", analysis_data.get("product", {}).get("category", "")],
                ["Date", self._now_str()],
            ],
            colWidths=[40 * mm, 110 * mm],
        )
        meta.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                    ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ]
            )
        )
        story.append(meta)
        story.append(Spacer(1, 10))

        # Overall status
        overall = analysis_data.get("overall_status", "UNKNOWN")
        summary = analysis_data.get("summary", {})
        head_data = [
            [
                Paragraph(f"<b>Overall Status: {overall}</b>", self.styles["Normal"]),
                Paragraph(
                    f"PASS {summary.get('PASS', 0)} &nbsp; "
                    f"FAIL {summary.get('FAIL', 0)} &nbsp; "
                    f"REVIEW {summary.get('REVIEW', 0)} &nbsp; "
                    f"N/A {summary.get('NOT_APPLICABLE', 0)}",
                    self.styles["Normal"],
                ),
            ]
        ]
        head = Table(head_data, colWidths=[80 * mm, 70 * mm])
        head.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), _STATUS_COLORS.get(overall, colors.grey)),
                    ("TEXTCOLOR", (0, 0), (0, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(head)
        story.append(Spacer(1, 10))

        # Rules table
        rules = analysis_data.get("rules", [])
        if rules:
            story.append(Paragraph("<b>Rule Results</b>", self.styles["Heading3"]))
            rows = [["Rule", "Status", "Description", "Reason"]]
            for r in rules:
                rows.append(
                    [
                        f"Rule {r['rule_number']} ({r['category']})",
                        r["status"],
                        r["title"],
                        r["reason"],
                    ]
                )
            rule_table = Table(
                rows,
                colWidths=[35 * mm, 20 * mm, 45 * mm, 50 * mm],
                repeatRows=1,
            )
            style = [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
            # color the status cells
            for i, r in enumerate(rules, start=1):
                color = _STATUS_COLORS.get(r["status"], colors.black)
                style.append(("TEXTCOLOR", (1, i), (1, i), color))
            rule_table.setStyle(TableStyle(style))
            story.append(rule_table)

        # Limitations
        story.append(Spacer(1, 12))
        story.append(Paragraph("<b>Limitations</b>", self.styles["Heading3"]))
        story.append(
            Paragraph(
                "This report is generated from photographs of the product "
                "packaging. It reflects an image-based compliance assessment "
                "ONLY. Physical quantity, maximum permissible error, and "
                "sampling/testing requirements cannot be verified from an "
                "image and require physical examination by an authorised "
                "officer. This is NOT a legal certificate of compliance.",
                self.styles["Small"],
            )
        )

        doc.build(story)
        return report_path

    @staticmethod
    def _now_str() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
