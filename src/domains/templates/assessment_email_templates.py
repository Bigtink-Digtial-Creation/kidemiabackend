from datetime import datetime
from src.shared.contants import KIDEMIA_EMAIL_BANNER

# Shared Styles for consistency
BASE_STYLES = """
    body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }
    .container { max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0; }
    .banner { width: 100%; height: auto; display: block; }
    .content { padding: 35px; font-size: 16px; }
    .info-card { background-color: #f9fafb; border-radius: 10px; padding: 25px; margin: 20px 0; border-left: 4px solid #BF4C20; }
    .cta-button { display: inline-block; padding: 14px 28px; background-color: #F28729; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; text-align: center; }
    .footer { background-color: #f9fafb; padding: 30px; text-align: center; font-size: 13px; color: #6B7280; border-top: 1px solid #eee; }
    .footer-links a { color: #BF4C20; text-decoration: none; margin: 0 10px; font-weight: 500; }
    .alert-box { background-color: #FFF7ED; border: 1px solid #FFEDD5; padding: 15px; border-radius: 8px; margin: 20px 0; }
"""


def ward_assignment_template(
    student_name: str,
    guardian_name: str,
    assessment: dict,
    due_date: datetime = None,
    instructions: str = "",
    proctoring_enabled: bool = False,
    base_url: str = "https://exam.kidemia.net",
    banner_url: str = KIDEMIA_EMAIL_BANNER,
) -> str:
    due_date_str = (
        f"<p><strong>📅 Due Date:</strong> {due_date.strftime('%B %d, %Y at %I:%M %p')}</p>"
        if due_date
        else ""
    )
    instructions_str = (
        f"<div class='alert-box'><strong>Instructions:</strong><br>{instructions}</div>"
        if instructions
        else ""
    )

    proctoring_notice = ""
    if proctoring_enabled:
        proctoring_notice = """
        <div style="background-color: #FEF2F2; border: 1px solid #FEE2E2; padding: 15px; border-radius: 8px; color: #991B1B; margin-top: 15px;">
            <strong>⚠️ Proctoring Enabled:</strong> This assessment monitors activity and requires camera access.
        </div>
        """

    return f"""
    <!DOCTYPE html><html><head><style>{BASE_STYLES}</style></head>
    <body>
        <div class="container">
            <img src="{banner_url}" class="banner">
            <div class="content">
                <h2 style="color: #BF4C20; margin-top: 0;">New Assessment Assigned</h2>
                <p>Hi {student_name},</p>
                <p>Your Guardian, <strong>{guardian_name}</strong> has assigned a new assessment to your dashboard.</p>
                
                <div class="info-card">
                    <h3 style="margin-top: 0; color: #BF4C20;">{assessment.get("title")}</h3>
                    <p style="margin: 5px 0;"><strong>Subject:</strong> {assessment.get("subject", "General")}</p>
                    <p style="margin: 5px 0;"><strong>Duration:</strong> {assessment.get("duration_minutes", 0)} mins</p>
                    {due_date_str}
                </div>
                {instructions_str}
                {proctoring_notice}
                <div style="text-align: center;">
                    <a href="{base_url}/challenges/available" class="cta-button">Start Assessment</a>
                </div>
            </div>
            <div class="footer">
                <div class="footer-links"><a href="{base_url}/dashboard">My Dashboard</a> | <a href="https://kidemia.net/support">Help Center</a></div>
                <p>&copy; Kidemia. All rights reserved.</p>
            </div>
        </div>
    </body></html>
    """


def guardian_completion_template(
    guardian_name: str,
    ward_name: str,
    assessment: dict,
    score: float,
    percentage: float,
    passed: bool,
    auto_submitted: bool,
    base_url: str = "https://exam.kidemia.net",
    attempt_id: str = "",
    banner_url: str = KIDEMIA_EMAIL_BANNER,
) -> str:
    status_color = "#10B981" if passed else "#EF4444"
    status_text = "Passed" if passed else "Completed"

    auto_submit_notice = (
        "<div class='alert-box' style='color: #9A3412;'><strong>⏰ Time Expired:</strong> This session was automatically submitted.</div>"
        if auto_submitted
        else ""
    )

    return f"""
    <!DOCTYPE html><html><head><style>{BASE_STYLES}</style></head>
    <body>
        <div class="container">
            <img src="{banner_url}" class="banner">
            <div class="content">
                <h2 style="color: #BF4C20; margin-top: 0;">Assessment Completed</h2>
                <p>Hi {guardian_name},</p>
                <p><strong>{ward_name}</strong> has successfully submitted their assessment.</p>
                
                <div class="info-card" style="border-left-color: {status_color};">
                    <h3 style="margin-top: 0; color: #111827;">{assessment.get("title")}</h3>
                    <p style="font-size: 24px; margin: 10px 0; font-weight: bold; color: {status_color};">
                        {percentage:.0f}% <span style="font-size: 16px; font-weight: normal; color: #666;">({score} points)</span>
                    </p>
                    <p><strong>Status:</strong> <span style="color: {status_color}; font-weight: bold;">{status_text}</span></p>
                </div>
                {auto_submit_notice}
                <div style="text-align: center;">
                    <a href="{base_url}/guardian/reports/{attempt_id}" class="cta-button">View Full Report</a>
                </div>
            </div>
            <div class="footer">
                <div class="footer-links"><a href="{base_url}/guardian/dashboard">Dashboard</a> | <a href="https://kidemia.net/privacy">Privacy Policy</a></div>
                <p>&copy; Kidemia. All rights reserved.</p>
            </div>
        </div>
    </body></html>
    """


def guardian_violation_template(
    guardian_name: str,
    ward_name: str,
    assessment: dict,
    violation_type: str,
    violation_count: int,
    base_url: str = "https://exam.kidemia.net",
    banner_url: str = KIDEMIA_EMAIL_BANNER,
) -> str:
    return f"""
    <!DOCTYPE html><html><head><style>{BASE_STYLES}</style></head>
    <body>
        <div class="container">
            <img src="{banner_url}" class="banner">
            <div class="content">
                <h2 style="color: #DC2626; margin-top: 0;">⚠️ Proctoring Alert</h2>
                <p>Hi {guardian_name},</p>
                <p>Our system detected a potential violation during <strong>{ward_name}'s</strong> assessment session.</p>
                
                <div class="info-card" style="border-left-color: #DC2626; background-color: #FEF2F2;">
                    <p><strong>Assessment:</strong> {assessment.get("title")}</p>
                    <p><strong>Violation:</strong> {violation_type}</p>
                    <p><strong>Occurrences:</strong> {violation_count}</p>
                </div>
                
                <p style="font-size: 14px; color: #666;">We recommend reviewing the session recording or discussing this with your ward to ensure academic integrity.</p>

                <div style="text-align: center;">
                    <a href="{base_url}/guardian/monitoring" class="cta-button" style="background-color: #111827;">Review Evidence</a>
                </div>
            </div>
            <div class="footer">
                <p>This is an automated security notification.</p>
            </div>
        </div>
    </body></html>
    """


def due_date_reminder_template(
    student_name: str,
    assessment: dict,
    hours_until_due: int,
    base_url: str = "https://exam.kidemia.net",
    due_date: datetime = None,
    banner_url: str = KIDEMIA_EMAIL_BANNER,
) -> str:
    urgency = (
        "is due very soon!"
        if hours_until_due <= 1
        else f"is due in {hours_until_due} hours."
    )

    return f"""
    <!DOCTYPE html><html><head><style>{BASE_STYLES}</style></head>
    <body>
        <div class="container">
            <img src="{banner_url}" class="banner">
            <div class="content">
                <h2 style="color: #BF4C20; margin-top: 0;">Don't Miss Out!</h2>
                <p>Hi {student_name},</p>
                <p>Just a quick reminder that your assessment <strong>{urgency}</strong></p>
                
                <div class="info-card">
                    <h3 style="margin-top: 0; color: #111827;">{assessment.get("title")}</h3>
                    <p style="color: #BF4C20; font-weight: bold;">Due: {due_date.strftime("%B %d, %Y at %I:%M %p")}</p>
                </div>

                <div style="text-align: center;">
                    <a href="{base_url}/ward/assignments/{assessment.get("id")}" class="cta-button">Finish Now</a>
                </div>
            </div>
            <div class="footer">
                <p>Stay on track to reach your learning goals!</p>
            </div>
        </div>
    </body></html>
    """


def get_assessment_result_email_html(
    student_name: str,
    assessment_title: str,
    score: float,
    total_questions: int,
    passed: bool,
    base_url: str = "https://exam.kidemia.net",
    banner_url: str = KIDEMIA_EMAIL_BANNER,
) -> str:
    # Logic for visual feedback
    percentage = (score / total_questions) * 100 if total_questions > 0 else 0
    status_color = "#10B981" if passed else "#BF4C20"  # Success Green or Brand Rust
    status_text = "PASSED" if passed else "COMPLETED"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }}
            .container {{ max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0; }}
            .banner {{ width: 100%; height: auto; display: block; }}
            .content {{ padding: 35px; font-size: 16px; }}
            .result-card {{ text-align: center; background-color: #f9fafb; border-radius: 12px; padding: 30px; margin: 25px 0; border-top: 4px solid {status_color}; }}
            .score-circle {{ font-size: 48px; font-weight: bold; color: {status_color}; margin: 10px 0; }}
            .status-badge {{ display: inline-block; padding: 6px 16px; border-radius: 20px; color: #ffffff; background-color: {status_color}; font-weight: bold; font-size: 14px; letter-spacing: 1px; }}
            .cta-button {{ display: inline-block; padding: 14px 28px; background-color: #F28729; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 10px; }}
            .pdf-notice {{ background-color: #FFF7ED; border: 1px solid #FFEDD5; padding: 15px; border-radius: 8px; font-size: 14px; display: flex; align-items: center; justify-content: center; }}
            .footer {{ background-color: #f9fafb; padding: 30px; text-align: center; font-size: 13px; color: #6B7280; border-top: 1px solid #eee; }}
            .footer-links a {{ color: #BF4C20; text-decoration: none; margin: 0 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <img src="{banner_url}" alt="Kidemia Banner" class="banner">
            <div class="content">
                <h2 style="color: #111827; margin-top: 0;">Well Done, {student_name}!</h2>
                <p>You have successfully submitted your assessment for <strong>{assessment_title}</strong>. Your results have been calculated and are ready for review.</p>
                
                <div class="result-card">
                    <div class="status-badge">{status_text}</div>
                    <div class="score-circle">{percentage:.0f}%</div>
                    <p style="margin: 0; color: #6B7280;">You answered {int(score)} out of {total_questions} questions correctly.</p>
                </div>

                <div class="pdf-notice">
                    <span>📎 <strong>Note:</strong> We have attached a detailed PDF breakdown of your performance to this email.</span>
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <a href="{base_url}/dashboard" class="cta-button">View Detailed Analytics</a>
                </div>
            </div>
            <div class="footer">
                <div class="footer-links">
                    <a href="{base_url}/support">Help Center</a> | <a href="{base_url}/cccount/settings">Profile Settings</a>
                </div>
                <p>&copy; Kidemia. Empowering the next generation of thinkers.</p>
            </div>
        </div>
    </body>
    </html>
    """
