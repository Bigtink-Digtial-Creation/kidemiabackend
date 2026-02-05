from src.shared.contants import KIDEMIA_EMAIL_BANNER
from src.shared.utils.helpers import get_client_base_url


def get_welcome_email_html(
    user_name: str,
    user_type: str,
    app_name: str = "Kidemia",
    banner_url: str = KIDEMIA_EMAIL_BANNER,
):
    # Role-specific content logic
    bonus_section = ""
    onboarding_steps = ""
    base_url = ""

    if user_type.lower() == "student":
        base_url = get_client_base_url("user")
        bonus_section = """
            <div style="background-color: #FFF7ED; border: 2px dashed #F28729; padding: 20px; border-radius: 12px; text-align: center; margin: 20px 0;">
                <h3 style="color: #BF4C20; margin: 0;">🎉 Welcome Bonus!</h3>
                <p style="margin: 10px 0 0 0;">You’ve been credited with <strong>100 Kidemia Credits</strong> to jumpstart your learning journey. Explore, practice, and shine!</p>
            </div>
        """
        onboarding_steps = """
            <li><strong>Discover:</strong> Browse assessments tailored to your level.</li>
            <li><strong>Practice:</strong> Take your first test to see where you stand.</li>
            <li><strong>Achieve:</strong> Earn badges, track progress, and climb the leaderboard!</li>
        """
    elif user_type.lower() == "guardian":
        base_url = get_client_base_url("user")
        onboarding_steps = """
            <li><strong>Connect:</strong> Link your wards using their email addresses.</li>
            <li><strong>Guide:</strong> Assign assessments that help them grow.</li>
            <li><strong>Track:</strong> Monitor their progress and get real-time updates.</li>
            <li><strong>Support:</strong> Provide encouragement and celebrate their milestones.</li>
        """
    else:
        base_url = get_client_base_url("admin")
        onboarding_steps = """
            <li><strong>Oversee:</strong> Manage users and access the admin console.</li>
            <li><strong>Curate:</strong> Review and approve assessment categories.</li>
            <li><strong>Analyze:</strong> Track platform performance and insights.</li>
        """
    return f"""
    <!DOCTYPE html>
    <html>
    <head><style>
        body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }}
        .container {{ max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0; }}
        .banner {{ width: 100%; height: auto; display: block; }}
        .content {{ padding: 35px; font-size: 16px; }}
        .cta-button {{ display: inline-block; padding: 14px 28px; background-color: #F28729; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; }}
        .footer {{ background-color: #f9fafb; padding: 30px; text-align: center; font-size: 13px; color: #6B7280; border-top: 1px solid #eee; }}
    </style></head>
    <body>
        <div class="container">
            <img src="{banner_url}" class="banner">
            <div class="content">
                <h2 style="color: #BF4C20; margin-top: 0;">Welcome to {app_name}, {user_name}!</h2>
                <p>We’re excited to have you onboard! {app_name} makes learning engaging, measurable, and secure—your journey starts here.</p>
                
                {bonus_section}

                <h3 style="color: #111827;">Get started in 3 simple steps:</h3>
                <ul style="padding-left: 20px;">
                    {onboarding_steps}
                </ul>

                <div style="text-align: center;">
                    <a href="{base_url}/auth/login" class="cta-button">Go to Dashboard</a>

                </div>
                
                <p style="margin-top: 30px; font-size: 14px; color: #666;">
                    <strong>What’s next:</strong> Personalized recommendations, progress updates, and a safe proctored environment to support your growth.
                </p>
            </div>
            <div class="footer">
                <p>Need help? Contact our support team at support@kidemia.net</p>
                <p>&copy; {app_name} 2026</p>
            </div>
        </div>
    </body>
    </html>
    """


def get_auth_security_email_html(
    user_name: str,
    action_type: str,
    details: str = "",
    user_type: str = "student",
    banner_url: str = KIDEMIA_EMAIL_BANNER,
):
    # Customize based on action
    title = "Account Update"
    action_color = "#BF4C20"
    base_url = (
        get_client_base_url(user_type)
        if user_type.lower() == "student"
        else get_client_base_url("admin")
    )

    if action_type == "deletion_request":
        title = "Account Deletion Scheduled"
        details = "We have received a request to permanently delete your Kidemia account. This will take effect in 14 days."
    elif action_type == "login_alert":
        title = "New Login Detected"
        action_color = "#111827"

    return f"""
    <!DOCTYPE html>
    <html>
    <head><style>
        body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }}
        .container {{ max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0; }}
        .banner {{ width: 100%; height: auto; display: block; }}
        .content {{ padding: 35px; font-size: 16px; }}
        .warning-box {{ background-color: #FEF2F2; border-left: 4px solid {action_color}; padding: 20px; margin: 20px 0; }}
    </style></head>
    <body>
        <div class="container">
            <img src="{banner_url}" class="banner">
            <div class="content">
                <h2 style="color: {action_color}; margin-top: 0;">{title}</h2>
                <p>Hello {user_name},</p>
                <div class="warning-box">
                    {details}
                </div>
                <p>If you did not authorize this action, please secure your account immediately by changing your password or contacting support.</p>
                <div style="text-align: center; margin-top: 25px;">
                    <a href="{base_url}/account/settings" style="color: #F28729; font-weight: bold; text-decoration: none;">Review Account Security &rarr;</a>
                </div>
            </div>
            <div class="footer" style="text-align: center; padding: 20px; color: #6B7280; font-size: 12px;">
                Sent for security purposes to protect your Kidemia account.
            </div>
        </div>
    </body>
    </html>
    """


def get_guardian_link_invitation_html(
    student_name: str,
    guardian_email: str,
    app_name: str = "Kidemia",
    banner_url: str = KIDEMIA_EMAIL_BANNER,
):
    return f"""
    <!DOCTYPE html>
    <html>
    <head><style>
        body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }}
        .container {{ max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0; }}
        .banner {{ width: 100%; height: auto; display: block; }}
        .content {{ padding: 35px; font-size: 16px; }}
        .invite-card {{ background-color: #FFF7ED; border: 1px solid #FFEDD5; padding: 25px; border-radius: 12px; margin: 20px 0; border-left: 4px solid #BF4C20; }}
        .cta-button {{ display: inline-block; padding: 14px 28px; background-color: #F28729; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; }}
        .footer {{ background-color: #f9fafb; padding: 30px; text-align: center; font-size: 13px; color: #6B7280; border-top: 1px solid #eee; }}
    </style></head>
    <body>
        <div class="container">
            <img src="{banner_url}" class="banner">
            <div class="content">
                <h2 style="color: #BF4C20; margin-top: 0;">Learning Invitation for {student_name}</h2>
                <p>Hello,</p>
                <p><strong>{student_name}</strong> just joined <strong>{app_name}</strong> and has invited you to be their official guardian on the platform.</p>
                
                <div class="invite-card">
                    <h3 style="margin-top: 0; color: #BF4C20;">Why join as a Guardian?</h3>
                    <ul style="margin: 0; padding-left: 20px; color: #444;">
                        <li><strong>Assign challenges:</strong>Monitor {student_name} progress.</li>
                        <li><strong>Track Mastery:</strong> View detailed analytics on their strengths and weak areas.</li>
                        <li><strong>Safety First:</strong> Receive real-time alerts on proctoring and academic integrity.</li>
                    </ul>
                </div>

                <p>To Kidemia and link your account, simply click the button below to complete your registration using this email address: <strong>{guardian_email}</strong>.</p>

                <div style="text-align: center;">
                    <a href="https://exam.kidemia.net/auth/signup/guardian" class="cta-button">Accept Invitation</a>
                </div>
            </div>
            <div class="footer">
                <p>If you don't know {student_name}, you can safely ignore this email.</p>
                <p>&copy; {app_name} 2026 | Empowering Student Growth</p>
            </div>
        </div>
    </body>
    </html>
    """
