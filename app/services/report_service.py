"""PDF report generation using ReportLab.

Produces a professional compliance report matching the frontend display:
- Header with title and metadata
- Score display with grade
- Score bar (green >= 75, yellow 60-74, red < 60)
- Priority breakdown (Key Fields, Supporting, Extra)
- Product information
- Rule results table
- Extracted fields
- Disclaimer
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
    HRFlowable,
)
from reportlab.graphics.shapes import Drawing, Rect, String

from app.core.config import get_settings
from app.compliance.scoring import ComplianceScore, get_grade_description


# Color palette
PRIMARY_BLUE = colors.HexColor("#1565C0")
SUCCESS_GREEN = colors.HexColor("#16a34a")
WARNING_YELLOW = colors.HexColor("#f59e0b")
FAIL_RED = colors.HexColor("#dc2626")
LIGHT_GREY = colors.HexColor("#F5F5F5")
DARK_GREY = colors.HexColor("#424242")

_GRADE_COLORS = {
    "A+": SUCCESS_GREEN,
    "A": SUCCESS_GREEN,
    "B": WARNING_YELLOW,
    "C": colors.HexColor("#EF6C00"),
    "D": FAIL_RED,
    "F": FAIL_RED,
}


class ReportGenerator:
    """Generates a PDF compliance report matching the frontend display."""

    def __init__(self):
        self.settings = get_settings()
        self.styles = getSampleStyleSheet()
        self._add_custom_styles()

    def _add_custom_styles(self):
        self.styles.add(ParagraphStyle(
            "ReportTitle",
            parent=self.styles["Title"],
            fontSize=22,
            textColor=PRIMARY_BLUE,
            spaceAfter=4,
            spaceBefore=0,
        ))
        self.styles.add(ParagraphStyle(
            "Subtitle",
            parent=self.styles["Normal"],
            fontSize=11,
            textColor=DARK_GREY,
            spaceAfter=12,
        ))
        self.styles.add(ParagraphStyle(
            "SectionHeader",
            parent=self.styles["Heading2"],
            fontSize=14,
            textColor=PRIMARY_BLUE,
            spaceBefore=16,
            spaceAfter=8,
        ))
        self.styles.add(ParagraphStyle(
            "ScoreLarge",
            parent=self.styles["Normal"],
            fontSize=48,
            textColor=PRIMARY_BLUE,
            alignment=1,
        ))
        self.styles.add(ParagraphStyle(
            "GradeText",
            parent=self.styles["Normal"],
            fontSize=24,
            textColor=colors.white,
            alignment=1,
        ))
        self.styles.add(ParagraphStyle(
            "SmallGrey",
            parent=self.styles["Normal"],
            fontSize=8,
            textColor=colors.grey,
        ))
        self.styles.add(ParagraphStyle(
            "ParamName",
            parent=self.styles["Normal"],
            fontSize=9,
            textColor=DARK_GREY,
        ))
        self.styles.add(ParagraphStyle(
            "ParamValue",
            parent=self.styles["Normal"],
            fontSize=9,
            textColor=colors.black,
        ))
        self.styles.add(ParagraphStyle(
            "Disclaimer",
            parent=self.styles["Normal"],
            fontSize=7,
            textColor=colors.grey,
            spaceBefore=6,
        ))

    def generate(self, analysis_data: dict, compliance_score: ComplianceScore = None) -> Path:
        self.settings.REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = (
            self.settings.REPORT_DIR
            / f"analysis_{analysis_data['analysis_id']}.pdf"
        )

        doc = SimpleDocTemplate(
            str(report_path),
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
        )

        story = []
        story.extend(self._build_header(analysis_data))
        if compliance_score:
            story.extend(self._build_score_section(compliance_score))
        story.extend(self._build_product_info(analysis_data))
        if compliance_score:
            story.extend(self._build_parameters_table(compliance_score))
        story.extend(self._build_rules_table(analysis_data))
        story.extend(self._build_disclaimer())

        doc.build(story)
        return report_path

    def _build_header(self, analysis_data: dict) -> list:
        elements = []
        elements.append(Paragraph("Compliance Assessment Report", self.styles["ReportTitle"]))
        elements.append(Paragraph(
            "Legal Metrology (Packaged Commodities) Rules, 2011",
            self.styles["Subtitle"]
        ))
        elements.append(HRFlowable(width="100%", thickness=2, color=PRIMARY_BLUE))
        elements.append(Spacer(1, 8))

        status = analysis_data.get("overall_status", "PENDING")
        meta_data = [
            ["Report ID:", analysis_data.get("analysis_id", "N/A")[:12] + "..."],
            ["Generated:", self._now_str()],
            ["Overall Status:", status],
        ]

        meta_table = Table(meta_data, colWidths=[40 * mm, 120 * mm])
        meta_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), DARK_GREY),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(meta_table)

        return elements

    def _build_score_section(self, score: ComplianceScore) -> list:
        elements = []
        elements.append(Spacer(1, 12))

        grade_color = _GRADE_COLORS.get(score.grade, colors.grey)
        grade_desc = get_grade_description(score.grade)

        score_data = [
            [
                Paragraph(f"<b>{score.total_score:.0f}</b>", self.styles["ScoreLarge"]),
                self._create_grade_box(score.grade, grade_color),
            ],
            [
                Paragraph("COMPLIANCE SCORE", self.styles["SmallGrey"]),
                Paragraph(grade_desc, self.styles["SmallGrey"]),
            ]
        ]

        score_table = Table(score_data, colWidths=[100 * mm, 55 * mm])
        score_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
            ("BOX", (0, 0), (-1, -1), 1, colors.white),
            ("TOPPADDING", (0, 0), (-1, 0), 15),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ]))
        elements.append(score_table)

        elements.append(Spacer(1, 8))
        elements.append(self._create_score_bar(score.total_score))

        summary = score.get_summary()
        elements.append(Spacer(1, 8))
        elements.append(self._create_priority_summary(summary))

        return elements

    def _create_grade_box(self, grade: str, color: colors.Color) -> Table:
        grade_data = [[Paragraph(f"<b>{grade}</b>", self.styles["GradeText"])]]
        grade_table = Table(grade_data, colWidths=[40 * mm], rowHeights=[40 * mm])
        grade_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), color),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
            ("BOX", (0, 0), (0, 0), 0, color),
        ]))
        return grade_table

    def _create_score_bar(self, score: float) -> Drawing:
        d = Drawing(480, 30)
        d.add(Rect(0, 5, 460, 20, fillColor=colors.HexColor("#E0E0E0"), strokeColor=None))

        fill_width = (score / 100) * 460
        if score >= 75:
            bar_color = SUCCESS_GREEN
        elif score >= 60:
            bar_color = WARNING_YELLOW
        else:
            bar_color = FAIL_RED

        d.add(Rect(0, 5, fill_width, 20, fillColor=bar_color, strokeColor=None))
        d.add(String(465, 10, f"{score:.0f}%", fontSize=12, fillColor=DARK_GREY))

        return d

    def _create_priority_summary(self, summary: dict) -> Table:
        data = [
            [
                Paragraph("<b>Category</b>", self.styles["ParamName"]),
                Paragraph("<b>Detected</b>", self.styles["ParamName"]),
                Paragraph("<b>Score</b>", self.styles["ParamName"]),
                Paragraph("<b>Max</b>", self.styles["ParamName"]),
            ],
        ]

        priority_map = {
            "high_priority": ("Key Fields", colors.HexColor("#16a34a")),
            "medium_priority": ("Supporting", colors.HexColor("#6366f1")),
            "low_priority": ("Extra", colors.HexColor("#8b5cf6")),
        }

        for key, (label, color) in priority_map.items():
            p_data = summary.get(key, {"passed": 0, "count": 0, "score": 0, "max": 0})
            pct = round((p_data["score"] / p_data["max"] * 100)) if p_data["max"] else 0

            data.append([
                Paragraph(f'<font color="{color.hexval()}">{label}</font>', self.styles["ParamName"]),
                Paragraph(f"{p_data['passed']}/{p_data['count']}", self.styles["ParamValue"]),
                Paragraph(f"{p_data['score']:.1f}", self.styles["ParamValue"]),
                Paragraph(f"{p_data['max']:.1f}", self.styles["ParamValue"]),
            ])

        table = Table(data, colWidths=[55 * mm, 35 * mm, 35 * mm, 35 * mm])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))

        return table

    def _build_product_info(self, analysis_data: dict) -> list:
        elements = []
        elements.append(Paragraph("<b>Product Information</b>", self.styles["SectionHeader"]))

        product = analysis_data.get("product", {})

        info_data = [
            ["Product Name:", product.get("name", "N/A")],
            ["Category:", product.get("category", "N/A")],
            ["Subcategory:", product.get("subcategory", "N/A")],
            ["Classification Confidence:", f"{product.get('classification_confidence', 0) * 100:.0f}%"],
        ]

        info_table = Table(info_data, colWidths=[55 * mm, 110 * mm])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), DARK_GREY),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        elements.append(info_table)

        return elements

    def _build_parameters_table(self, score: ComplianceScore) -> list:
        elements = []
        elements.append(Paragraph("<b>Compliance Parameters</b>", self.styles["SectionHeader"]))

        data = [
            [
                Paragraph("<b>#</b>", self.styles["ParamName"]),
                Paragraph("<b>Parameter</b>", self.styles["ParamName"]),
                Paragraph("<b>Priority</b>", self.styles["ParamName"]),
                Paragraph("<b>Status</b>", self.styles["ParamName"]),
                Paragraph("<b>Value Detected</b>", self.styles["ParamName"]),
                Paragraph("<b>Score</b>", self.styles["ParamName"]),
            ]
        ]

        priority_colors = {
            "HIGH": colors.HexColor("#16a34a"),
            "MEDIUM": colors.HexColor("#6366f1"),
            "LOW": colors.HexColor("#8b5cf6"),
        }

        for i, param in enumerate(score.parameters, 1):
            status = "PASS" if param.present else "FAIL"
            status_color = SUCCESS_GREEN if param.present else FAIL_RED
            priority_color = priority_colors.get(param.priority, colors.black)

            data.append([
                Paragraph(str(i), self.styles["ParamValue"]),
                Paragraph(param.name, self.styles["ParamValue"]),
                Paragraph(f'<font color="{priority_color.hexval()}">{param.priority}</font>',
                         self.styles["ParamValue"]),
                Paragraph(f'<font color="{status_color.hexval()}">{status}</font>',
                         self.styles["ParamValue"]),
                Paragraph(param.value[:25] + "..." if len(param.value) > 25 else param.value,
                         self.styles["ParamValue"]),
                Paragraph(f"{param.points:.1f}/{param.weight * 100:.1f}", self.styles["ParamValue"]),
            ])

        table = Table(data, colWidths=[12 * mm, 45 * mm, 25 * mm, 20 * mm, 40 * mm, 25 * mm])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(table)

        return elements

    def _build_rules_table(self, analysis_data: dict) -> list:
        elements = []

        rules = analysis_data.get("rules", [])
        if not rules:
            return elements

        elements.append(Paragraph("<b>Rule Results</b>", self.styles["SectionHeader"]))

        status_colors = {
            "PASS": SUCCESS_GREEN,
            "FAIL": FAIL_RED,
            "REVIEW": WARNING_YELLOW,
            "NOT_APPLICABLE": colors.grey,
        }

        data = [
            [
                Paragraph("<b>Rule</b>", self.styles["ParamName"]),
                Paragraph("<b>Status</b>", self.styles["ParamName"]),
                Paragraph("<b>Title</b>", self.styles["ParamName"]),
                Paragraph("<b>Reason</b>", self.styles["ParamName"]),
            ]
        ]

        for rule in rules[:15]:
            status = rule.get("status", "UNKNOWN")
            status_color = status_colors.get(status, colors.black)

            data.append([
                Paragraph(f"R{rule.get('rule_number', rule.get('rule', '?'))}", self.styles["ParamValue"]),
                Paragraph(f'<font color="{status_color.hexval()}">{status}</font>',
                         self.styles["ParamValue"]),
                Paragraph(rule.get("title", "")[:35], self.styles["ParamValue"]),
                Paragraph(rule.get("reason", "")[:45], self.styles["ParamValue"]),
            ])

        table = Table(data, colWidths=[15 * mm, 25 * mm, 55 * mm, 65 * mm])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), DARK_GREY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(table)

        return elements

    def _build_disclaimer(self) -> list:
        elements = []
        elements.append(Spacer(1, 15))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        elements.append(Spacer(1, 6))

        disclaimer_text = (
            "<b>DISCLAIMER:</b> This report is generated from photographs of the product "
            "packaging using OCR and automated analysis. It reflects an image-based compliance "
            "assessment ONLY. Physical quantity verification, maximum permissible error "
            "calculation, and sampling/testing requirements cannot be verified from images "
            "and require physical examination by an authorised officer. This is NOT a legal "
            "certificate of compliance. For official verification, please contact the "
            "relevant Legal Metrology authority."
        )

        elements.append(Paragraph(disclaimer_text, self.styles["Disclaimer"]))

        footer_data = [
            ["Generated by:", "Packaged Commodities Compliance System"],
            ["Reference:", "Legal Metrology (Packaged Commodities) Rules, 2011"],
            ["Act:", "Legal Metrology Act, 2009"],
        ]

        footer_table = Table(footer_data, colWidths=[35 * mm, 120 * mm])
        footer_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(Spacer(1, 8))
        elements.append(footer_table)

        return elements

    @staticmethod
    def _now_str() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
