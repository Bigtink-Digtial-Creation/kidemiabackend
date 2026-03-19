from io import BytesIO
from datetime import datetime
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from src.domains.institution.schemas.analytics import StudentReportCard


# ── Colour palette (matches your orange theme) ───────────────────
ORANGE = colors.HexColor("#e07b39")
ORANGE_LIGHT = colors.HexColor("#fff4ed")
GREEN = colors.HexColor("#10b981")
RED = colors.HexColor("#ef4444")
GRAY = colors.HexColor("#6b7280")
GRAY_LIGHT = colors.HexColor("#f9fafb")
DARK = colors.HexColor("#111827")
WHITE = colors.white


def _grade_color(score: float):
    if score >= 75:
        return GREEN
    if score >= 60:
        return ORANGE
    return RED


def _letter_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _trend_symbol(trend: str) -> str:
    return {
        "improving": "↑ Improving",
        "declining": "↓ Declining",
        "stable": "→ Stable",
    }.get(trend, "— N/A")


def generate_report_card_pdf(card: StudentReportCard) -> bytes:
    """Generate a single student report card as PDF bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    # styles = getSampleStyleSheet()
    story = []

    # ── Header ────────────────────────────────────────────────────
    header_data = [
        [
            Paragraph(
                "<font color='#e07b39'><b>STUDENT REPORT CARD</b></font>",
                ParagraphStyle("h", fontSize=16, leading=20),
            ),
            Paragraph(
                f"Generated: {datetime.now().strftime('%d %b %Y')}",
                ParagraphStyle("r", fontSize=9, textColor=GRAY, alignment=TA_RIGHT),
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=["70%", "30%"])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=8))

    # ── Student info block ────────────────────────────────────────
    info_data = [
        ["Student", card.student_name, "Code", card.student_code or "—"],
        [
            "Classroom",
            card.classroom_name or "Unassigned",
            "Guardian",
            card.guardian_email or "—",
        ],
    ]
    info_table = Table(info_data, colWidths=["15%", "35%", "15%", "35%"])
    info_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), GRAY),
                ("TEXTCOLOR", (2, 0), (2, -1), GRAY),
                ("TEXTCOLOR", (1, 0), (1, -1), DARK),
                ("TEXTCOLOR", (3, 0), (3, -1), DARK),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [GRAY_LIGHT, WHITE]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [GRAY_LIGHT, WHITE]),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 8))

    # ── Summary scores ────────────────────────────────────────────
    avg = card.overall_avg_score
    summary_data = [
        ["Overall Average", "Pass Rate", "Completion", "Grade", "Rank", "Trend"],
        [
            Paragraph(
                f"<b><font color='{_grade_color(avg).hexval() if hasattr(_grade_color(avg), 'hexval') else '#10b981'}'>{avg}%</font></b>",
                ParagraphStyle("c", fontSize=13, alignment=TA_CENTER),
            ),
            f"{card.overall_pass_rate}%",
            f"{card.completion_rate}%",
            Paragraph(
                f"<b>{card.grade}</b>",
                ParagraphStyle("c", fontSize=13, alignment=TA_CENTER),
            ),
            f"#{card.rank_in_class} / {card.class_size}" if card.rank_in_class else "—",
            _trend_symbol(card.trend),
        ],
    ]
    summary_table = Table(
        summary_data, colWidths=["18%", "16%", "16%", "14%", "18%", "18%"]
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ORANGE),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("PADDING", (0, 0), (-1, -1), 7),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [ORANGE_LIGHT]),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # ── Subject performance ───────────────────────────────────────
    if card.subject_performance:
        story.append(
            Paragraph(
                "<b>Subject Performance</b>",
                ParagraphStyle("sh", fontSize=10, textColor=DARK, spaceAfter=4),
            )
        )
        subj_header = ["Subject", "Assessments", "Avg Score", "Pass Rate", "Best Score"]
        subj_rows = [subj_header] + [
            [
                s.subject_name,
                str(s.total_assessments),
                f"{s.avg_score}%",
                f"{s.pass_rate}%",
                f"{s.best_score}%",
            ]
            for s in card.subject_performance
        ]
        subj_table = Table(subj_rows, colWidths=["30%", "18%", "18%", "18%", "16%"])
        subj_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
                ]
            )
        )
        story.append(subj_table)
        story.append(Spacer(1, 10))

    # ── Assessment results ────────────────────────────────────────
    if card.assessment_results:
        story.append(
            Paragraph(
                "<b>Assessment Results</b>",
                ParagraphStyle("sh", fontSize=10, textColor=DARK, spaceAfter=4),
            )
        )
        res_header = ["Assessment", "Subject", "Score", "Grade", "Attempts", "Status"]
        res_rows = [res_header]
        for r in card.assessment_results:
            score_str = f"{r.percentage}%" if r.percentage is not None else "—"
            res_rows.append(
                [
                    Paragraph(r.assessment_title[:45], ParagraphStyle("t", fontSize=7)),
                    r.subject_name or "—",
                    score_str,
                    r.grade or "—",
                    str(r.attempt_count),
                    r.status.replace("_", " ").title(),
                ]
            )
        res_table = Table(
            res_rows,
            colWidths=["32%", "18%", "12%", "10%", "12%", "16%"],
        )
        res_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (2, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
                ]
            )
        )
        story.append(res_table)

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY, spaceAfter=4))
    story.append(
        Paragraph(
            f"This report was generated automatically by the platform on {datetime.now().strftime('%d %b %Y at %H:%M')}.",
            ParagraphStyle("footer", fontSize=7, textColor=GRAY, alignment=TA_CENTER),
        )
    )

    doc.build(story)
    return buffer.getvalue()


def generate_bulk_report_cards_pdf(cards: List[StudentReportCard]) -> bytes:
    """Merge all report cards into a single PDF, one page break per student."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    # styles = getSampleStyleSheet()
    story = []

    for i, card in enumerate(cards):
        # Re-use the single card story builder but collect flowables
        card_story = _build_card_story(card)
        story.extend(card_story)
        if i < len(cards) - 1:
            story.append(PageBreak())

    doc.build(story)
    return buffer.getvalue()


def _build_card_story(card: StudentReportCard) -> list:
    """Return the reportlab flowables for a single card (used by bulk generator)."""
    # Duplicate of generate_report_card_pdf logic but returns story list
    # rather than building the doc — avoids code duplication
    tmp_buffer = BytesIO()
    tmp_doc = SimpleDocTemplate(
        tmp_buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    story = []

    header_data = [
        [
            Paragraph(
                "<font color='#e07b39'><b>STUDENT REPORT CARD</b></font>",
                ParagraphStyle("h", fontSize=16, leading=20),
            ),
            Paragraph(
                f"Generated: {datetime.now().strftime('%d %b %Y')}",
                ParagraphStyle("r", fontSize=9, textColor=GRAY, alignment=TA_RIGHT),
            ),
        ]
    ]
    ht = Table(header_data, colWidths=["70%", "30%"])
    ht.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(ht)
    story.append(HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=8))

    info_data = [
        ["Student", card.student_name, "Code", card.student_code or "—"],
        [
            "Classroom",
            card.classroom_name or "Unassigned",
            "Guardian",
            card.guardian_email or "—",
        ],
    ]
    it = Table(info_data, colWidths=["15%", "35%", "15%", "35%"])
    it.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), GRAY),
                ("TEXTCOLOR", (2, 0), (2, -1), GRAY),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [GRAY_LIGHT, WHITE]),
            ]
        )
    )
    story.append(it)
    story.append(Spacer(1, 8))

    avg = card.overall_avg_score
    summary_data = [
        ["Overall Average", "Pass Rate", "Completion", "Grade", "Rank", "Trend"],
        [
            f"{avg}%",
            f"{card.overall_pass_rate}%",
            f"{card.completion_rate}%",
            card.grade,
            f"#{card.rank_in_class} / {card.class_size}" if card.rank_in_class else "—",
            _trend_symbol(card.trend),
        ],
    ]
    st = Table(summary_data, colWidths=["18%", "16%", "16%", "14%", "18%", "18%"])
    st.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ORANGE),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("PADDING", (0, 0), (-1, -1), 7),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [ORANGE_LIGHT]),
            ]
        )
    )
    story.append(st)
    story.append(Spacer(1, 8))

    if card.subject_performance:
        story.append(
            Paragraph(
                "<b>Subject Performance</b>",
                ParagraphStyle("sh", fontSize=10, textColor=DARK, spaceAfter=4),
            )
        )
        rows = [["Subject", "Assessments", "Avg Score", "Pass Rate", "Best Score"]] + [
            [
                s.subject_name,
                str(s.total_assessments),
                f"{s.avg_score}%",
                f"{s.pass_rate}%",
                f"{s.best_score}%",
            ]
            for s in card.subject_performance
        ]
        subj_t = Table(rows, colWidths=["30%", "18%", "18%", "18%", "16%"])
        subj_t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
                ]
            )
        )
        story.append(subj_t)
        story.append(Spacer(1, 8))

    if card.assessment_results:
        story.append(
            Paragraph(
                "<b>Assessment Results</b>",
                ParagraphStyle("sh", fontSize=10, textColor=DARK, spaceAfter=4),
            )
        )
        rows = [["Assessment", "Subject", "Score", "Grade", "Attempts", "Status"]] + [
            [
                Paragraph(r.assessment_title[:45], ParagraphStyle("t", fontSize=7)),
                r.subject_name or "—",
                f"{r.percentage}%" if r.percentage is not None else "—",
                r.grade or "—",
                str(r.attempt_count),
                r.status.replace("_", " ").title(),
            ]
            for r in card.assessment_results
        ]
        res_t = Table(rows, colWidths=["32%", "18%", "12%", "10%", "12%", "16%"])
        res_t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (2, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
                ]
            )
        )
        story.append(res_t)

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY, spaceAfter=4))
    story.append(
        Paragraph(
            f"Generated automatically on {datetime.now().strftime('%d %b %Y at %H:%M')}.",
            ParagraphStyle("footer", fontSize=7, textColor=GRAY, alignment=TA_CENTER),
        )
    )

    return story
