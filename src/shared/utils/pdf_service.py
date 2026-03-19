import io
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("Agg")  # Use non-GUI backend
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)
from reportlab.lib.units import inch


class PDFService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.primary_color = colors.HexColor("#BF4C20")
        self.secondary_color = colors.HexColor("#F28729")

        # RGB values for matplotlib
        self.primary_rgb = (191 / 255, 76 / 255, 32 / 255)
        self.secondary_rgb = (242 / 255, 135 / 255, 41 / 255)

        # Custom Styles
        self.styles.add(
            ParagraphStyle(
                name="KidemiaHeader",
                parent=self.styles["Heading1"],
                fontSize=24,
                textColor=self.secondary_color,
                spaceAfter=20,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="ResultLabel",
                fontSize=14,
                textColor=colors.grey,
                alignment=1,  # Center
            )
        )

    def _get_mastery_color(self, level: str):
        mapping = {
            "MASTERED": colors.darkgreen,
            "PROFICIENT": colors.green,
            "DEVELOPING": colors.orange,
            "NEEDS_WORK": self.primary_color,
        }
        return mapping.get(level, colors.black)

    def _create_mastery_pie_chart(self, analytics: dict) -> Image:
        """Create a professional pie chart using matplotlib"""
        # Count mastery levels
        mastery_counts = {
            "Mastered": 0,
            "Proficient": 0,
            "Developing": 0,
            "Needs Work": 0,
        }

        mapping = {
            "MASTERED": "Mastered",
            "PROFICIENT": "Proficient",
            "DEVELOPING": "Developing",
            "NEEDS_WORK": "Needs Work",
        }

        for item in analytics["all_topics"]:
            level = mapping.get(item["mastery_level"], "Needs Work")
            mastery_counts[level] += 1

        # Filter out zero values
        labels = [k for k, v in mastery_counts.items() if v > 0]
        sizes = [v for v in mastery_counts.values() if v > 0]
        colors_list = ["#006400", "#32CD32", "#FFA500", "#BF4C20"][: len(labels)]

        # Create figure
        fig, ax = plt.subplots(figsize=(6, 4))
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors_list,
            autopct="%1.1f%%",
            startangle=90,
            textprops={"fontsize": 10},
        )

        # Style the percentage text
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_weight("bold")

        ax.set_title("Mastery Level Distribution", fontsize=14, weight="bold", pad=20)

        # Save to buffer
        img_buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(img_buffer, format="png", dpi=150, bbox_inches="tight")
        plt.close()
        img_buffer.seek(0)

        return Image(img_buffer, width=4 * inch, height=2.7 * inch)

    def _create_subject_bar_chart(self, analytics: dict) -> Image:
        """Create a bar chart showing performance by subject"""
        # Aggregate data by subject
        subject_data = {}
        for item in analytics["all_topics"]:
            subject = item["subject_name"]
            if subject not in subject_data:
                subject_data[subject] = {"correct": 0, "total": 0}
            subject_data[subject]["correct"] += item["correct_answers"]
            subject_data[subject]["total"] += item["questions_attempted"]

        # Calculate percentages
        subjects = list(subject_data.keys())
        percentages = [
            (subject_data[s]["correct"] / subject_data[s]["total"] * 100)
            if subject_data[s]["total"] > 0
            else 0
            for s in subjects
        ]

        # Create figure
        fig, ax = plt.subplots(figsize=(7, 4))
        bars = ax.bar(
            subjects,
            percentages,
            color=self.secondary_rgb,
            edgecolor="black",
            linewidth=1.2,
        )

        # Color bars based on performance
        for i, (bar, pct) in enumerate(zip(bars, percentages)):
            if pct >= 80:
                bar.set_color("#006400")  # Dark green
            elif pct >= 60:
                bar.set_color("#32CD32")  # Green
            elif pct >= 40:
                bar.set_color("#FFA500")  # Orange
            else:
                bar.set_color(self.primary_rgb)  # Red

        ax.set_ylabel("Score (%)", fontsize=11, weight="bold")
        ax.set_xlabel("Subject", fontsize=11, weight="bold")
        ax.set_title("Performance by Subject", fontsize=14, weight="bold", pad=15)
        ax.set_ylim(0, 100)
        ax.grid(axis="y", alpha=0.3, linestyle="--")

        # Rotate x labels if many subjects
        if len(subjects) > 4:
            plt.xticks(rotation=45, ha="right")

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{height:.1f}%",
                ha="center",
                va="bottom",
                fontsize=9,
                weight="bold",
            )

        # Save to buffer
        img_buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(img_buffer, format="png", dpi=150, bbox_inches="tight")
        plt.close()
        img_buffer.seek(0)

        return Image(img_buffer, width=5 * inch, height=2.8 * inch)

    def _create_topic_performance_chart(self, analytics: dict) -> Image:
        """Create horizontal bar chart for top/bottom topics"""
        # Get all topics with their scores
        topics_with_scores = []
        for item in analytics["all_topics"]:
            if item["questions_attempted"] > 0:
                score_pct = (
                    item["correct_answers"] / item["questions_attempted"]
                ) * 100
                topics_with_scores.append(
                    {
                        "name": item["topic_name"][:35],  # Truncate long names
                        "score": score_pct,
                    }
                )

        # Sort by score
        topics_with_scores.sort(key=lambda x: x["score"], reverse=True)

        # Get top 8 (or all if less)
        display_count = min(8, len(topics_with_scores))
        top_topics = topics_with_scores[:display_count]

        topic_names = [t["name"] for t in top_topics]
        scores = [t["score"] for t in top_topics]

        # Reverse for better display (highest at top)
        topic_names.reverse()
        scores.reverse()

        # Create figure
        fig, ax = plt.subplots(figsize=(6, max(4, display_count * 0.5)))

        # Create bars with color gradient
        colors_list = []
        for score in scores:
            if score >= 80:
                colors_list.append("#006400")
            elif score >= 60:
                colors_list.append("#32CD32")
            elif score >= 40:
                colors_list.append("#FFA500")
            else:
                colors_list.append("#BF4C20")

        bars = ax.barh(
            topic_names, scores, color=colors_list, edgecolor="black", linewidth=1
        )

        ax.set_xlabel("Score (%)", fontsize=11, weight="bold")
        ax.set_title("Topic Performance", fontsize=14, weight="bold", pad=15)
        ax.set_xlim(0, 100)
        ax.grid(axis="x", alpha=0.3, linestyle="--")

        # Add value labels
        for i, (bar, score) in enumerate(zip(bars, scores)):
            ax.text(
                score + 2,
                bar.get_y() + bar.get_height() / 2,
                f"{score:.1f}%",
                va="center",
                fontsize=9,
                weight="bold",
            )

        # Save to buffer
        img_buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(img_buffer, format="png", dpi=150, bbox_inches="tight")
        plt.close()
        img_buffer.seek(0)

        height = max(3, display_count * 0.4)
        return Image(img_buffer, width=5 * inch, height=height * inch)

    async def generate_detailed_report(self, base_data: dict, analytics: dict) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        # Header
        elements.append(
            Paragraph(
                f"Kidemia Analytics: {base_data['student_name']}",
                self.styles["KidemiaHeader"],
            )
        )
        elements.append(Spacer(1, 0.2 * inch))

        # Mastery Distribution Chart
        elements.append(
            Paragraph("Overall Performance Overview", self.styles["Heading2"])
        )
        elements.append(Spacer(1, 0.15 * inch))
        elements.append(self._create_mastery_pie_chart(analytics))
        elements.append(Spacer(1, 0.3 * inch))

        # Subject Performance Chart
        elements.append(Paragraph("Performance by Subject", self.styles["Heading2"]))
        elements.append(Spacer(1, 0.15 * inch))
        elements.append(self._create_subject_bar_chart(analytics))
        elements.append(Spacer(1, 0.3 * inch))

        # Topic Performance Chart
        elements.append(Paragraph("Top Performing Topics", self.styles["Heading2"]))
        elements.append(Spacer(1, 0.15 * inch))
        elements.append(self._create_topic_performance_chart(analytics))
        elements.append(Spacer(1, 0.3 * inch))

        # Detailed Table
        elements.append(PageBreak())  # New page for detailed data
        elements.append(
            Paragraph("Detailed Subject & Topic Performance", self.styles["Heading2"])
        )
        elements.append(Spacer(1, 0.15 * inch))

        table_data = [["Subject", "Topic", "Score", "Mastery"]]
        for item in analytics["all_topics"]:
            table_data.append(
                [
                    item["subject_name"],
                    item["topic_name"],
                    f"{item['correct_answers']}/{item['questions_attempted']}",
                    Paragraph(
                        f"<font color='{self._get_mastery_color(item['mastery_level'])}'>{item['mastery_level']}</font>",
                        self.styles["Normal"],
                    ),
                ]
            )

        t = Table(
            table_data, colWidths=[1.2 * inch, 2.5 * inch, 0.8 * inch, 1.5 * inch]
        )
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), self.primary_color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elements.append(t)
        elements.append(Spacer(1, 0.3 * inch))

        # Personalized Study Plan
        if analytics.get("recommended_for_practice"):
            elements.append(PageBreak())
            elements.append(
                Paragraph("Personalized Study Plan", self.styles["Heading2"])
            )
            elements.append(Spacer(1, 0.2 * inch))

            for rec in analytics["recommended_for_practice"]:
                elements.append(
                    Paragraph(
                        f"<b>Focus Area: {rec['topic_name']}</b>", self.styles["Normal"]
                    )
                )
                elements.append(
                    Paragraph(f"<i>Why? {rec['reason']}</i>", self.styles["Normal"])
                )

                for test in rec["suggested_assessments"][:2]:
                    elements.append(
                        Paragraph(
                            f"• Practice: {test['title']} ({test['difficulty']})",
                            self.styles["Normal"],
                        )
                    )
                elements.append(Spacer(1, 0.15 * inch))

        doc.build(elements)
        return buffer.getvalue()
