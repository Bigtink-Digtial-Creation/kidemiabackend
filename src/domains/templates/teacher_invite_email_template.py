from datetime import datetime, timezone

from src.shared.contants import KIDEMIA_EMAIL_BANNER


def get_teacher_invitation_html(
    teacher_name,
    teacher_email,
    institution_name,
    temp_password,
    user_type,
    app_name: str = "Kidemia",
    banner_url: str = KIDEMIA_EMAIL_BANNER,
) -> str:

    year = datetime.now(timezone.utc)
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background: #ffffff;
                border-radius: 8px;
                overflow: hidden;
                border: 1px solid #e0e0e0;
            }}
            .banner {{
                width: 100%;
                height: auto;
                display: block;
            }}
            .content {{
                padding: 35px;
                font-size: 16px;
            }}
            .cta-button {{
                display: inline-block;
                padding: 14px 28px;
                background-color: #F28729;
                color: #ffffff !important;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
                margin-top: 25px;
            }}
            .credential-box {{
                background-color: #FFF7ED;
                border: 1px solid #FFEDD5;
                border-radius: 8px;
                padding: 20px 25px;
                margin: 20px 0;
            }}
            .credential-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 0;
                border-bottom: 1px solid #FFEDD5;
            }}
            .credential-row:last-child {{
                border-bottom: none;
            }}
            .credential-label {{
                color: #92400E;
                font-size: 13px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .credential-value {{
                font-family: monospace;
                font-size: 15px;
                color: #C2410C;
                font-weight: 700;
                background: #fff;
                padding: 4px 10px;
                border-radius: 4px;
                border: 1px solid #FED7AA;
            }}
            .steps {{
                background-color: #F9FAFB;
                padding: 25px;
                border-radius: 8px;
                margin-top: 25px;
                border: 1px solid #E5E7EB;
            }}
            .steps ol {{
                margin-top: 15px;
                padding-left: 20px;
            }}
            .steps li {{
                margin-bottom: 12px;
            }}
            .warning-box {{
                background-color: #FEF3C7;
                border: 1px solid #FDE68A;
                border-radius: 8px;
                padding: 15px 20px;
                margin-top: 20px;
                font-size: 14px;
                color: #92400E;
            }}
            .footer {{
                background-color: #f9fafb;
                padding: 30px;
                text-align: center;
                font-size: 13px;
                color: #6B7280;
                border-top: 1px solid #eee;
            }}
            .footer-links {{
                margin-bottom: 15px;
            }}
            .footer-links a {{
                color: #F28729;
                text-decoration: none;
                margin: 0 10px;
                font-weight: 500;
            }}
            .highlight {{
                color: #F28729;
                font-weight: 600;
            }}
            .divider {{
                border: none;
                border-top: 1px solid #E5E7EB;
                margin: 25px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <img src="{banner_url}" alt="{app_name} Banner" class="banner">

            <div class="content">
                <p>Hello <strong>{teacher_name}</strong>,</p>

                <p>
                    You have been invited to join
                    <span class="highlight">{institution_name}</span>
                    as a <span class="highlight">Teacher</span> on the
                    <strong>{app_name}</strong> platform.
                </p>

                <p>
                    Your account has been created and is ready to use.
                    Below are your login credentials — please keep them safe.
                </p>

                <!-- Credentials -->
                <div class="credential-box">
                    <p style="margin: 0 0 15px 0; font-weight: 700; color: #92400E; font-size: 15px;">
                        Your Login Credentials
                    </p>
                    <div class="credential-row">
                        <span class="credential-label">Email</span>
                        <span class="credential-value">{teacher_email}</span>
                    </div>
                    <div class="credential-row">
                        <span class="credential-label">Temp Password</span>
                        <span class="credential-value">{temp_password}</span>
                    </div>
                </div>

                <div class="warning-box">
                    ⚠️ <strong>Important:</strong> This is a temporary password.
                    You will be required to change it on your first login.
                    Do not share this email with anyone.
                </div>

                <hr class="divider">

                <!-- Steps -->
                <div class="steps">
                    <strong style="font-size: 17px; color: #C2410C;">Getting Started</strong>
                    <ol>
                        <li>
                            <strong>Verify your email:</strong> There is a 
                            second email eith a verification link.
                        </li>
                        <li>
                            <strong>Log in:</strong> Use the credentials above to sign in
                            to the institution dashboard.
                        </li>
                        <li>
                            <strong>Change your password:</strong> This is import to
                            secure your account.
                        </li>
                        <li>
                            <strong>Explore your dashboard:</strong> View your assigned
                            classrooms, students, and assessments.
                        </li>
                    </ol>
                </div>

                 

                <p style="margin-top: 30px; font-size: 14px; color: #6B7280;">
                    If you were not expecting this invitation or believe this was sent
                    in error, you can safely ignore this email. Your account will
                    remain inactive until you verify your email.
                </p>
            </div>

            <div class="footer">
                <div class="footer-links">
                    <a href="https://kidemia.net/support">Help Center</a> |
                    <a href="https://exam.kidemia.net/institution/dashboard">My Dashboard</a> |
                    <a href="https://kidemia.net/privacy">Privacy Policy</a>
                </div>
                <p>&copy; {year} {app_name}. All rights reserved.</p>
                <p style="font-size: 11px;">Sent on {date_str}</p>
            </div>
        </div>
    </body>
    </html>
    """
