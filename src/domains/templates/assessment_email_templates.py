from datetime import datetime


def ward_assignment_template(
    student_name: str,
    guardian_name: str,
    assessment: dict,
    due_date: datetime = None,
    instructions: str = "",
    proctoring_enabled: bool = False,
    base_url: str = "",
) -> str:
    due_date_str = (
        f"<p><strong>Due Date:</strong> {due_date.strftime('%B %d, %Y at %I:%M %p')}</p>"
        if due_date
        else ""
    )
    instructions_str = (
        f"<div style='background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;'><p><strong>Instructions:</strong></p><p>{instructions}</p></div>"
        if instructions
        else ""
    )
    proctoring_notice = (
        "<div style='background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;'><p style='margin:0; color:#856404;'><strong>⚠️ Proctoring Enabled</strong></p><p style='margin:5px 0 0 0;color:#856404;font-size:14px;'>This assessment requires camera access and monitors your activity.</p></div>"
        if proctoring_enabled
        else ""
    )

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{font-family: Arial,sans-serif; background:#f4f6f8; margin:0; padding:0;}}
            .container {{max-width:600px; margin:40px auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 4px 12px rgba(0,0,0,0.1);}}
            .header {{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); padding:40px 30px; text-align:center; color:#fff;}}
            .content {{padding:40px 30px; color:#333; line-height:1.6;}}
            .btn {{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); color:#fff; padding:12px 30px; text-decoration:none; border-radius:5px; display:inline-block;}}
            .footer {{background:#f8f9fa; padding:20px 30px; font-size:12px; color:#999; text-align:center;}}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📚 New Assessment Assigned</h1>
            </div>
            <div class="content">
                <p>Hi {student_name},</p>
                <p><strong>{guardian_name}</strong> has assigned you a new assessment:</p>
                <div style="background:#f8f9fa; border-radius:10px; padding:25px; margin:20px 0;">
                    <h2 style="margin:0 0 15px 0; color:#667eea;">{assessment.get("title")}</h2>
                    <p style="margin:0;color:#666;font-size:14px;"><strong>Subject:</strong> {assessment.get("subject", "N/A")}</p>
                    <p style="margin:0;color:#666;font-size:14px;"><strong>Questions:</strong> {assessment.get("total_questions", 0)}</p>
                    <p style="margin:0;color:#666;font-size:14px;"><strong>Duration:</strong> {assessment.get("duration_minutes", 0)} minutes</p>
                    <p style="margin:0;color:#666;font-size:14px;"><strong>Max Attempts:</strong> {assessment.get("max_attempts", 1)}</p>
                </div>
                {due_date_str}
                {instructions_str}
                {proctoring_notice}
                <p style="text-align:center; margin:30px 0;">
                    <a href="{base_url}/ward/assignments/{assessment.get("id")}" class="btn">View Assignment</a>
                </p>
                <p style="font-size:14px; color:#666; text-align:center;">Good luck! 🎯</p>
            </div>
            <div class="footer">
                You received this email because you are enrolled as a ward.
            </div>
        </div>
    </body>
    </html>
    """


def guardian_completion_template(
    guardian_name: str,
    ward_name: str,
    assessment: dict,
    score: float,
    percentage: float,
    passed: bool,
    auto_submitted: bool,
    base_url: str,
    attempt_id: str,
) -> str:
    status_color = "#10b981" if passed else "#ef4444"
    status_text = "Passed ✓" if passed else "Failed ✗"
    auto_submit_notice = (
        "<div style='background:#fff3cd; border-left:4px solid #ffc107; padding:15px; margin:20px 0;'><p style='margin:0;color:#856404;'><strong>⏰ Auto-Submitted</strong></p><p style='margin:5px 0 0 0;color:#856404;font-size:14px;'>This assessment was automatically submitted when the time expired.</p></div>"
        if auto_submitted
        else ""
    )

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{font-family:Arial,sans-serif;background:#f4f6f8;margin:0;padding:0;}}
            .container {{max-width:600px;margin:40px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.1);}}
            .header {{background:linear-gradient(135deg,#3b82f6 0%,#1e40af 100%);padding:40px 30px;text-align:center;color:#fff;}}
            .content {{padding:40px 30px;color:#333;line-height:1.6;}}
            .btn {{background:linear-gradient(135deg,#3b82f6 0%,#1e40af 100%); color:#fff; padding:12px 30px; text-decoration:none; border-radius:5px; display:inline-block;}}
            .footer {{background:#f8f9fa;padding:20px 30px;font-size:12px;color:#999;text-align:center;}}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h1>📊 Assessment Completed</h1></div>
            <div class="content">
                <p>Hi {guardian_name},</p>
                <p><strong>{ward_name}</strong> has completed an assessment:</p>
                <div style="background:#f8f9fa; border-radius:10px; padding:25px; margin:20px 0;">
                    <h2 style="margin:0 0 20px 0; color:#3b82f6;">{assessment.get("title")}</h2>
                    <p style="font-size:16px;"><strong>Score:</strong> {score} ({percentage:.0f}%)</p>
                    <p style="font-size:16px;"><strong>Status:</strong> <span style="color:{status_color}; font-weight:600;">{status_text}</span></p>
                </div>
                {auto_submit_notice}
                <p style="text-align:center; margin:30px 0;">
                    <a href="{base_url}/guardian/assignments/{attempt_id}" class="btn">View Detailed Results</a>
                </p>
            </div>
            <div class="footer">You received this email because you are registered as a guardian.</div>
        </div>
    </body>
    </html>
    """


def guardian_violation_template(
    guardian_name: str,
    ward_name: str,
    assessment: dict,
    violation_type: str,
    violation_count: int,
    base_url: str,
) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{font-family:Arial,sans-serif;background:#f4f6f8;margin:0;padding:0;}}
            .container {{max-width:600px;margin:40px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.1);}}
            .header {{background:linear-gradient(135deg,#f59e0b 0%,#dc2626 100%);padding:40px 30px;text-align:center;color:#fff;}}
            .content {{padding:40px 30px;color:#333;line-height:1.6;}}
            .btn {{background:linear-gradient(135deg,#f59e0b 0%,#dc2626 100%); color:#fff; padding:12px 30px; text-decoration:none; border-radius:5px; display:inline-block;}}
            .footer {{background:#f8f9fa;padding:20px 30px;font-size:12px;color:#999;text-align:center;}}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h1>⚠️ Proctoring Alert</h1></div>
            <div class="content">
                <p>Hi {guardian_name},</p>
                <p>A proctoring violation has been detected during an assessment:</p>
                <div style="background:#fef3c7; border-left:4px solid #f59e0b; border-radius:10px; padding:25px; margin:20px 0;">
                    <p><strong>Ward:</strong> {ward_name}</p>
                    <p><strong>Assessment:</strong> {assessment.get("title")}</p>
                    <p><strong>Violation Type:</strong> {violation_type}</p>
                    <p><strong>Occurrences:</strong> {violation_count}</p>
                </div>
                <p style="text-align:center; margin:30px 0;">
                    <a href="{base_url}/guardian/assignments" class="btn">View Monitoring Dashboard</a>
                </p>
            </div>
            <div class="footer">You received this alert because proctoring monitoring is active.</div>
        </div>
    </body>
    </html>
    """


def due_date_reminder_template(
    student_name: str,
    assessment: dict,
    hours_until_due: int,
    base_url: str,
    due_date: datetime,
) -> str:
    urgency_message = (
        "is due very soon!"
        if hours_until_due <= 1
        else f"is due in {hours_until_due} hours"
    )
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{font-family:Arial,sans-serif;background:#f4f6f8;margin:0;padding:0;}}
            .container {{max-width:600px;margin:40px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.1);}}
            .header {{background:linear-gradient(135deg,#f59e0b 0%,#ea580c 100%);padding:40px 30px;text-align:center;color:#fff;}}
            .content {{padding:40px 30px;color:#333;line-height:1.6;}}
            .btn {{background:linear-gradient(135deg,#f59e0b 0%,#ea580c 100%); color:#fff; padding:12px 30px; text-decoration:none; border-radius:5px; display:inline-block;}}
            .footer {{background:#f8f9fa;padding:20px 30px;font-size:12px;color:#999;text-align:center;}}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h1>⏰ Assessment Due Soon</h1></div>
            <div class="content">
                <p>Hi {student_name},</p>
                <p>This is a friendly reminder that your assessment <strong>{urgency_message}</strong></p>
                <div style="background:#fef3c7; border-radius:10px; padding:25px; margin:20px 0;">
                    <h2 style="margin:0 0 15px 0; color:#92400e;">{assessment.get("title")}</h2>
                    <p style="margin:0;color:#78350f;font-size:16px;font-weight:600;">Due: {due_date.strftime("%B %d, %Y at %I:%M %p")}</p>
                </div>
                <p style="text-align:center; margin:30px 0;">
                    <a href="{base_url}/ward/assignments/{assessment.get("id")}" class="btn">Start Assessment Now</a>
                </p>
            </div>
            <div class="footer">You received this reminder to help you stay on track.</div>
        </div>
    </body>
    </html>
    """
