"""PDF report generation using ReportLab.

Produces a professional compliance report limited to 2 A4 pages:
- Header with title and metadata (IST timestamps)
- Score display with grade, bar, and priority summary
- Product information
- Rule results table with sequential # and internal legal rule ID
- Disclaimer

All timestamps are displayed in IST (Asia/Kolkata).
Score normalization is correct: points/weight (not weight*100).
"""

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

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
    KeepTogether,
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

# Compact fonts
FONT_SIZE_TITLE = 16
FONT_SIZE_SUBTITLE = 9
FONT_SIZE_SECTION = 11
FONT_SIZE_BODY = 8
FONT_SIZE_SMALL = 7
FONT_SIZE_TINY = 6
ROW_PAD = 3


class ReportGenerator:
    """Generates a professional 2-page PDF compliance report."""

    def __init__(self):
        self.settings = get_settings()
        self.styles = getSampleStyleSheet()
        self._add_custom_styles()

    def _add_custom_styles(self):
        self.styles.add(ParagraphStyle(
            "ReportTitle", parent=self.styles["Title"],
            fontSize=FONT_SIZE_TITLE, textColor=PRIMARY_BLUE,
            spaceAfter=2, spaceBefore=0,
        ))
        self.styles.add(ParagraphStyle(
            "Subtitle", parent=self.styles["Normal"],
            fontSize=FONT_SIZE_SUBTITLE, textColor=DARK_GREY,
            spaceAfter=6,
        ))
        self.styles.add(ParagraphStyle(
            "SectionHeader", parent=self.styles["Heading2"],
            fontSize=FONT_SIZE_SECTION, textColor=PRIMARY_BLUE,
            spaceBefore=8, spaceAfter=4,
        ))
        self.styles.add(ParagraphStyle(
            "ScoreLarge", parent=self.styles["Normal"],
            fontSize=36, textColor=PRIMARY_BLUE, alignment=1,
        ))
        self.styles.add(ParagraphStyle(
            "GradeText", parent=self.styles["Normal"],
            fontSize=20, textColor=colors.white, alignment=1,
        ))
        self.styles.add(ParagraphStyle(
            "SmallGrey", parent=self.styles["Normal"],
            fontSize=FONT_SIZE_TINY, textColor=colors.grey,
        ))
        self.styles.add(ParagraphStyle(
            "ParamName", parent=self.styles["Normal"],
            fontSize=FONT_SIZE_SMALL, textColor=DARK_GREY,
        ))
        self.styles.add(ParagraphStyle(
            "ParamValue", parent=self.styles["Normal"],
            fontSize=FONT_SIZE_SMALL, textColor=colors.black,
        ))
        self.styles.add(ParagraphStyle(
            "Disclaimer", parent=self.styles["Normal"],
            fontSize=FONT_SIZE_TINY, textColor=colors.grey,
            spaceBefore=4,
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
            rightMargin=12 * mm,
            leftMargin=12 * mm,
            topMargin=10 * mm,
            bottomMargin=10 * mm,
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
        elements.append(Paragraph("LegalMetriX Compliance Report", self.styles["ReportTitle"]))
        elements.append(Paragraph(
            "Legal Metrology (Packaged Commodities) Rules, 2011",
            self.styles["Subtitle"]
        ))
        elements.append(HRFlowable(width="100%", thickness=2, color=PRIMARY_BLUE))
        elements.append(Spacer(1, 4))

        status = analysis_data.get("overall_status", "PENDING")
        meta_data = [
            ["Report ID:", analysis_data.get("analysis_id", "N/A")[:16] + "...", "Status:", status],
            ["Generated:", self._now_str(), "", ""],
        ]

        meta_table = Table(meta_data, colWidths=[28 * mm, 65 * mm, 22 * mm, 65 * mm])
        meta_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), FONT_SIZE_SMALL),
            ("TEXTCOLOR", (0, 0), (0, -1), DARK_GREY),
            ("TEXTCOLOR", (2, 0), (2, -1), DARK_GREY),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(meta_table)
        return elements

    def _build_score_section(self, score: ComplianceScore) -> list:
        elements = []
        elements.append(Spacer(1, 6))

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

        score_table = Table(score_data, colWidths=[100 * mm, 48 * mm])
        score_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
            ("BOX", (0, 0), (-1, -1), 1, colors.white),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ]))
        elements.append(score_table)

        elements.append(Spacer(1, 4))
        elements.append(self._create_score_bar(score.total_score))

        summary = score.get_summary()
        elements.append(Spacer(1, 4))
        elements.append(self._create_priority_summary(summary))

        return elements

    def _create_grade_box(self, grade: str, color: colors.Color) -> Table:
        grade_data = [[Paragraph(f"<b>{grade}</b>", self.styles["GradeText"])]]
        grade_table = Table(grade_data, colWidths=[36 * mm], rowHeights=[36 * mm])
        grade_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), color),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
            ("BOX", (0, 0), (0, 0), 0, color),
        ]))
        return grade_table

    def _create_score_bar(self, score: float) -> Drawing:
        d = Drawing(480, 22)
        d.add(Rect(0, 3, 460, 16, fillColor=colors.HexColor("#E0E0E0"), strokeColor=None))
        fill_width = (score / 100) * 460
        if score >= 50:
            bar_color = SUCCESS_GREEN
        elif score >= 30:
            bar_color = WARNING_YELLOW
        else:
            bar_color = FAIL_RED
        d.add(Rect(0, 3, fill_width, 16, fillColor=bar_color, strokeColor=None))
        d.add(String(465, 5, f"{score:.0f}%", fontSize=10, fillColor=DARK_GREY))
        return d

    def _create_priority_summary(self, summary: dict) -> Table:
        data = [[
            Paragraph("<b>Priority</b>", self.styles["ParamName"]),
            Paragraph("<b>Passed</b>", self.styles["ParamName"]),
            Paragraph("<b>Total</b>", self.styles["ParamName"]),
            Paragraph("<b>Score</b>", self.styles["ParamName"]),
            Paragraph("<b>Max</b>", self.styles["ParamName"]),
            Paragraph("<b>%</b>", self.styles["ParamName"]),
        ]]

        priority_map = {
            "essential": ("Essential", colors.HexColor("#16a34a")),
            "supporting": ("Supporting", colors.HexColor("#6366f1")),
        }

        for key, (label, color) in priority_map.items():
            p_data = summary.get(key, {"passed": 0, "count": 0, "score": 0, "max": 0, "percentage": 0})
            pct = p_data.get("percentage", 0)
            data.append([
                Paragraph(f'<font color="{color.hexval()}">{label}</font>', self.styles["ParamName"]),
                Paragraph(f"{p_data['passed']}", self.styles["ParamValue"]),
                Paragraph(f"{p_data['count']}", self.styles["ParamValue"]),
                Paragraph(f"{p_data['score']:.1f}", self.styles["ParamValue"]),
                Paragraph(f"{p_data['max']:.1f}", self.styles["ParamValue"]),
                Paragraph(f"{pct:.0f}%", self.styles["ParamValue"]),
            ])

        table = Table(data, colWidths=[32 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), FONT_SIZE_SMALL),
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), ROW_PAD),
            ("TOPPADDING", (0, 0), (-1, -1), ROW_PAD),
        ]))
        return table

    def _build_product_info(self, analysis_data: dict) -> list:
        elements = []
        elements.append(Paragraph("<b>Product Information</b>", self.styles["SectionHeader"]))

        product = analysis_data.get("product", {})
        info_data = [
            ["Name:", product.get("name", "N/A"), "Category:", product.get("category", "N/A")],
            ["Subcategory:", product.get("subcategory", "N/A"),
             "Confidence:", f"{product.get('classification_confidence', 0) * 100:.0f}%"],
        ]

        info_table = Table(info_data, colWidths=[30 * mm, 58 * mm, 30 * mm, 50 * mm])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), FONT_SIZE_SMALL),
            ("TEXTCOLOR", (0, 0), (0, -1), DARK_GREY),
            ("TEXTCOLOR", (2, 0), (2, -1), DARK_GREY),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        elements.append(info_table)
        return elements

    def _build_parameters_table(self, score: ComplianceScore) -> list:
        elements = []
        elements.append(Paragraph("<b>Compliance Parameters</b>", self.styles["SectionHeader"]))

        data = [[
            Paragraph("<b>#</b>", self.styles["ParamName"]),
            Paragraph("<b>Parameter</b>", self.styles["ParamName"]),
            Paragraph("<b>Priority</b>", self.styles["ParamName"]),
            Paragraph("<b>Status</b>", self.styles["ParamName"]),
            Paragraph("<b>Score</b>", self.styles["ParamName"]),
        ]]

        priority_colors = {
            "ESSENTIAL": colors.HexColor("#16a34a"),
            "SUPPORTING": colors.HexColor("#6366f1"),
        }

        for i, param in enumerate(score.parameters, 1):
            status = "PASS" if param.present else "FAIL"
            status_color = SUCCESS_GREEN if param.present else FAIL_RED
            priority_color = priority_colors.get(param.priority, colors.black)

            data.append([
                Paragraph(str(i), self.styles["ParamValue"]),
                Paragraph(param.name[:45] + "..." if len(param.name) > 45 else param.name,
                          self.styles["ParamValue"]),
                Paragraph(f'<font color="{priority_color.hexval()}">{param.priority}</font>',
                          self.styles["ParamValue"]),
                Paragraph(f'<font color="{status_color.hexval()}">{status}</font>',
                          self.styles["ParamValue"]),
                Paragraph(f"{param.points:.1f}/{param.weight:.1f}", self.styles["ParamValue"]),
            ])

        table = Table(data, colWidths=[10 * mm, 60 * mm, 28 * mm, 22 * mm, 25 * mm])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), FONT_SIZE_SMALL),
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), ROW_PAD),
            ("TOPPADDING", (0, 0), (-1, -1), ROW_PAD),
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
        priority_colors = {
            "HIGH": colors.HexColor("#16a34a"),
            "MEDIUM": colors.HexColor("#6366f1"),
        }

        data = [[
            Paragraph("<b>#</b>", self.styles["ParamName"]),
            Paragraph("<b>Rule (Internal ID)</b>", self.styles["ParamName"]),
            Paragraph("<b>Priority</b>", self.styles["ParamName"]),
            Paragraph("<b>Status</b>", self.styles["ParamName"]),
            Paragraph("<b>Detail</b>", self.styles["ParamName"]),
        ]]

        for i, rule in enumerate(rules[:12], 1):
            status = rule.get("status", "UNKNOWN")
            status_color = status_colors.get(status, colors.black)
            severity = rule.get("severity", "")
            pri_color = priority_colors.get(severity, colors.black)
            pri_label = "Essential" if severity == "HIGH" else "Supporting"

            rule_id_label = rule.get("rule_id", "") or f"LM-{rule.get('rule', '')}"
            data.append([
                Paragraph(f"{i}", self.styles["ParamValue"]),
                Paragraph(
                    f'{rule.get("title", "")[:28]}<br/>'
                    f'<font size="5" color="#94a3b8">{rule_id_label}</font>',
                    self.styles["ParamValue"]),
                Paragraph(f'<font color="{pri_color.hexval()}">{pri_label}</font>',
                          self.styles["ParamValue"]),
                Paragraph(f'<font color="{status_color.hexval()}">{status}</font>',
                          self.styles["ParamValue"]),
                Paragraph(rule.get("reason", "")[:32] if rule.get("reason") else "", self.styles["ParamValue"]),
            ])

        table = Table(data, colWidths=[10 * mm, 48 * mm, 26 * mm, 22 * mm, 52 * mm])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), FONT_SIZE_SMALL),
            ("BACKGROUND", (0, 0), (-1, 0), DARK_GREY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), ROW_PAD),
            ("TOPPADDING", (0, 0), (-1, -1), ROW_PAD),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(table)
        return elements

    def _build_disclaimer(self) -> list:
        elements = []
        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        elements.append(Spacer(1, 3))

        disclaimer_text = (
            "<b>DISCLAIMER:</b> This report is generated from photographs of the product "
            "packaging using OCR and automated analysis. It reflects an image-based compliance "
            "assessment ONLY. Physical quantity verification and sampling/testing requirements "
            "require physical examination. This is NOT a legal certificate of compliance."
        )
        elements.append(Paragraph(disclaimer_text, self.styles["Disclaimer"]))

        footer_data = [
            ["Generated by: LegalMetriX", "Reference: Legal Metrology (Packaged Commodities) Rules, 2011"],
        ]
        footer_table = Table(footer_data, colWidths=[80 * mm, 95 * mm])
        footer_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), FONT_SIZE_TINY),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(Spacer(1, 4))
        elements.append(footer_table)
        return elements

    @staticmethod
    def _now_str() -> str:
        ist = ZoneInfo("Asia/Kolkata")
        return datetime.now(timezone.utc).astimezone(ist).strftime("%d %B %Y, %I:%M %p IST")
