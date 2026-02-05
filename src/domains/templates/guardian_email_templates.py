from src.shared.contants import KIDEMIA_EMAIL_BANNER
from src.shared.events.payloads import CategoryChangeApproved, CategoryChangePayload


def get_ward_invitation_html(
    payload, app_name: str = "Kidemia", banner_url: str = KIDEMIA_EMAIL_BANNER
):
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
            .cta-button {{ display: inline-block; padding: 14px 28px; background-color: #F28729; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 25px; }}
            .steps {{ background-color: #FFF7ED; padding: 25px; border-radius: 8px; margin-top: 25px; border: 1px solid #FFEDD5; }}
            .footer {{ background-color: #f9fafb; padding: 30px; text-align: center; font-size: 13px; color: #6B7280; border-top: 1px solid #eee; }}
            .footer-links {{ margin-bottom: 15px; }}
            .footer-links a {{ color: #F28729; text-decoration: none; margin: 0 10px; font-weight: 500; }}
            .highlight {{ color: #F28729; font-weight: 600; }}
            .guardian-box {{ background: #eee; padding: 10px; border-radius: 4px; font-family: monospace; display: block; margin: 10px 0; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <img src="{banner_url}" alt="{app_name} Banner" class="banner">
            <div class="content">
                <p>Hello,</p>
                <p>You have been invited to join the <strong>{app_name}</strong> assessment platform as a ward by your <span class="highlight">{payload["relationship_type"]}</span>.</p>
                
                <p>By joining, your guardian can assign specialized assessments to help track your learning progress and unlock new skills.</p>
                
                <div class="steps">
                    <strong style="font-size: 18px; color: #C2410C;">Getting Started</strong>
                    <ol style="margin-top: 15px; padding-left: 20px;">
                        <li style="margin-bottom: 10px;"><strong>Visit the Portal:</strong> Click the button below to go to the registration page.</li>
                        <li style="margin-bottom: 10px;"><strong>Required Detail:</strong> During registration, you <strong>must</strong> enter the following email in the <strong>"Guardian Email"</strong> field to link your account:</li>
                    </ol>
                    <div class="guardian-box">{payload["guardian_email"]}</div>
                </div>

                <div style="text-align: center;">
                    <a href="https://exam.kidemia.net/auth/signup" class="cta-button">Create Your Account</a>
                </div>
            </div>
            <div class="footer">
                <div class="footer-links">
                    <a href="https://kidemia.net/support">Help Center</a> | 
                    <a href="https://exam.kidemia.net/dashboard">My Dashboard</a> | 
                    <a href="https://kidemia.net/privacy">Privacy Policy</a>
                </div>
                <p>&copy; {payload["date"].year} {app_name}. All rights reserved.</p>
                <p style="font-size: 11px;">Sent on {payload["date"].strftime("%B %d, %Y")}</p>
            </div>
        </div>
    </body>
    </html>
    """


def get_ward_removal_html(
    payload, app_name: str = "Kidemia", banner_url: str = KIDEMIA_EMAIL_BANNER
):
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
            .notice-box {{ border-left: 4px solid #F28729; background-color: #FFF7ED; padding: 20px; margin: 20px 0; border-radius: 0 8px 8px 0; }}
            .footer {{ background-color: #f9fafb; padding: 30px; text-align: center; font-size: 13px; color: #6B7280; border-top: 1px solid #eee; }}
            .footer-links {{ margin-bottom: 15px; }}
            .footer-links a {{ color: #F28729; text-decoration: none; margin: 0 10px; font-weight: 500; }}
        </style>
    </head>
    <body>
        <div class="container">
            <img src="{banner_url}" alt="{app_name} Banner" class="banner">
            <div class="content">
                <h2 style="color: #111827; margin-top: 0;">Account Unlinked</h2>
                <p>Hello,</p>
                <p>This email is to confirm that your account has been unlinked from your <span style="font-weight:600; color: #F28729;">{payload["relationship_type"]}</span> ({payload["guardian_email"]}).</p>
                
                <div class="notice-box">
                    <strong>Important Changes:</strong>
                    <ul style="margin-top: 10px; padding-left: 20px;">
                        <li>Your previous guardian no longer has access to your data.</li>
                        <li>Any incomplete assessments assigned by them have been moved to your archive.</li>
                        <li>Your personal learning history and score data remain secure and accessible to you.</li>
                    </ul>
                </div>

                <p><strong>Next Steps:</strong><br>
                You can continue using {app_name} independently. If you need to link a new guardian, teacher, or parent, you can provide their email in your account settings at any time.</p>
            </div>
            <div class="footer">
                <div class="footer-links">
                    <a href="https://kidemia.net/support">Help Center</a> | 
                    <a href="https://exam.kidemia.net/dashboard">Go to Dashboard</a>
                </div>
                <p>&copy; {payload["date"].year} {app_name}. All rights reserved.</p>
                <p style="font-size: 11px;">Processed on {payload["date"].strftime("%B %d, %Y at %H:%M")}</p>
            </div>
        </div>
    </body>
    </html>
    """


def get_category_change_request_html(
    payload: CategoryChangePayload,
    app_name: str = "Kidemia",
    banner_url: str = KIDEMIA_EMAIL_BANNER,
):
    reason_text = payload["reason"] if payload["reason"] else "No reason provided."
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
            .change-box {{ background-color: #f9fafb; border: 1px solid #eee; border-radius: 8px; padding: 20px; margin: 20px 0; display: flex; align-items: center; justify-content: center; text-align: center; }}
            .category-tag {{ background: #eee; padding: 5px 12px; border-radius: 4px; font-weight: bold; font-size: 14px; }}
            .arrow {{ color: #F28729; font-size: 20px; margin: 0 15px; font-weight: bold; }}
            .reason-section {{ border-left: 4px solid #F28729; padding-left: 15px; font-style: italic; color: #555; margin: 20px 0; }}
            .cta-button {{ display: inline-block; padding: 14px 28px; background-color: #F28729; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 10px; }}
            .footer {{ background-color: #f9fafb; padding: 30px; text-align: center; font-size: 13px; color: #6B7280; border-top: 1px solid #eee; }}
            .footer-links a {{ color: #F28729; text-decoration: none; margin: 0 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <img src="{banner_url}" alt="{app_name} Banner" class="banner">
            <div class="content">
                <h2 style="color: #111827; margin-top: 0;">Category Change Request</h2>
                <p>Hello,</p>
                <p><strong>{payload["student_name"]}</strong> has requested to change their learning category. This change, if approved, will update the algorithm, assessments and content they see on the platform.</p>
                
                <div class="change-box">
                    <span class="category-tag">{payload["old_category"]}</span>
                    <span class="arrow">&rarr;</span>
                    <span class="category-tag" style="background: #FFF7ED; color: #C2410C; border: 1px solid #FFEDD5;">{payload["new_category"]}</span>
                </div>

                <p><strong>Reason provided:</strong></p>
                <div class="reason-section">
                    "{reason_text}"
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <a href="https://exam.kidemia.net/guardian/category-requests" class="cta-button">Review Request</a>
                </div>
            </div>
            <div class="footer">
                <div class="footer-links">
                    <a href="https://kidemia.net/support">Support</a> | <a href="https://exam.kidemia.net/guardian">Guardian Dashboard</a>
                </div>
                <p>&copy; {app_name}. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """


def get_category_decision_html(
    payload: CategoryChangeApproved,
    app_name: str = "Kidemia",
    banner_url: str = KIDEMIA_EMAIL_BANNER,
):
    is_approved = payload["state"] == "approved"
    status_color = "#10B981" if is_approved else "#EF4444"
    status_text = "Approved" if is_approved else "Declined"

    message = (
        f"Great news! Your request to move to <strong>{payload['new_category']}</strong> has been approved. Your dashboard has been updated with new content."
        if is_approved
        else f"Your request to move to {payload['new_category']} was not approved at this time. You will continue learning in the <strong>{payload['old_category']}</strong> category."
    )

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
            .status-badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; color: #ffffff; font-weight: bold; font-size: 12px; text-transform: uppercase; background-color: {status_color}; margin-bottom: 15px; }}
            .info-card {{ background-color: #f9fafb; padding: 20px; border-radius: 8px; border-top: 3px solid {status_color}; margin: 20px 0; }}
            .footer {{ background-color: #f9fafb; padding: 30px; text-align: center; font-size: 13px; color: #6B7280; border-top: 1px solid #eee; }}
            .footer-links a {{ color: #F28729; text-decoration: none; margin: 0 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <img src="{banner_url}" alt="{app_name} Banner" class="banner">
            <div class="content">
                <div class="status-badge">{status_text}</div>
                <h2 style="color: #111827; margin-top: 0;">Category Request Update</h2>
                <p>Hello,</p>
                <div class="info-card">
                    {message}
                </div>
                <p>If you have questions about this decision, please reach out to your guardian directly.</p>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="https://exam.kidemia.net/dashboard" style="display: inline-block; padding: 14px 28px; background-color: #F28729; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: bold;">Go to Dashboard</a>
                </div>
            </div>
            <div class="footer">
                <div class="footer-links">
                    <a href="https://kidemia.net/support">Help Center</a> | <a href="https://exam.kidemia.net/account/settings">Account Settings</a>
                </div>
                <p>&copy; {app_name}. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
