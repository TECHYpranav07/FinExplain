"""
Email Service for Transactional Emails via Brevo (Sendinblue) API.
Handles delivery of 6-digit OTP codes for password reset with HTML formatting
and local development fallback logging.
"""

import logging
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def generate_otp_email_html(otp_code: str, name: Optional[str] = None) -> str:
    """Generate a sleek, responsive HTML email template for password reset OTP."""
    recipient_greeting = f"Hello {name}," if name else "Hello,"
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Password Reset Verification Code</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #0c0c0e;
      color: #f4f4f5;
      margin: 0;
      padding: 30px 15px;
    }}
    .container {{
      max-width: 520px;
      margin: 0 auto;
      background-color: #18181b;
      border: 1px solid #27272a;
      border-radius: 16px;
      padding: 32px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }}
    .header {{
      display: flex;
      align-items: center;
      margin-bottom: 24px;
      border-bottom: 1px solid #27272a;
      padding-bottom: 16px;
    }}
    .logo-badge {{
      background-color: #ffffff;
      color: #000000;
      font-weight: 800;
      font-size: 14px;
      padding: 6px 12px;
      border-radius: 8px;
      display: inline-block;
      margin-right: 10px;
    }}
    .brand-name {{
      font-size: 18px;
      font-weight: 700;
      color: #ffffff;
      letter-spacing: -0.5px;
    }}
    h2 {{
      color: #ffffff;
      font-size: 20px;
      margin-top: 0;
      margin-bottom: 12px;
    }}
    p {{
      color: #a1a1aa;
      font-size: 14px;
      line-height: 1.6;
      margin: 12px 0;
    }}
    .otp-box {{
      background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
      border: 1px solid #3f3f46;
      border-radius: 12px;
      padding: 20px;
      text-align: center;
      margin: 24px 0;
    }}
    .otp-code {{
      font-family: 'Courier New', Courier, monospace;
      font-size: 36px;
      font-weight: 800;
      letter-spacing: 8px;
      color: #ffffff;
      display: inline-block;
    }}
    .expiry-badge {{
      display: inline-block;
      background-color: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.3);
      color: #fbbf24;
      font-size: 12px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 6px;
      margin-top: 10px;
    }}
    .footer {{
      margin-top: 30px;
      padding-top: 20px;
      border-top: 1px solid #27272a;
      font-size: 12px;
      color: #71717a;
      line-height: 1.5;
    }}
    .footer strong {{
      color: #d4d4d8;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <span class="logo-badge">Fx</span>
      <span class="brand-name">FinExplain Security</span>
    </div>
    
    <h2>Reset Your Password</h2>
    <p>{recipient_greeting}</p>
    <p>We received a request to reset your password for your FinExplain account. Enter the verification code below on the password reset screen to continue:</p>
    
    <div class="otp-box">
      <div class="otp-code">{otp_code}</div>
      <div>
        <span class="expiry-badge">⏱ Valid for 5 minutes</span>
      </div>
    </div>
    
    <p>If you didn't request a password reset, you can safely ignore this email. Your current password will remain unchanged and your account is secure.</p>
    
    <div class="footer">
      <strong>Security Tip:</strong> Never share this 6-digit code with anyone. FinExplain staff will never ask for your verification code.
    </div>
  </div>
</body>
</html>
"""


async def send_brevo_otp_email(
    to_email: str,
    otp_code: str,
    name: Optional[str] = None
) -> bool:
    """
    Send transactional OTP email via Brevo REST API.
    If BREVO_API_KEY is not configured, logs the OTP to console for dev testing.
    """
    api_key = settings.BREVO_API_KEY
    from_email = settings.BREVO_FROM_EMAIL or "no-reply@finexplain.com"
    from_name = getattr(settings, "BREVO_FROM_NAME", "FinExplain Security")

    # If Brevo API key is not set, log OTP clearly for development/testing
    if not api_key:
        logger.warning(
            f"========================================================\n"
            f"[DEV MODE] BREVO_API_KEY is not configured.\n"
            f"🔑 Verification OTP for {to_email} is: {otp_code}\n"
            f"⏱ Valid for 5 minutes (300s)\n"
            f"========================================================"
        )
        return True

    payload = {
        "sender": {
            "name": from_name,
            "email": from_email,
        },
        "to": [
            {
                "email": to_email,
                "name": name or to_email.split("@")[0].title(),
            }
        ],
        "subject": f"FinExplain Verification Code: {otp_code}",
        "htmlContent": generate_otp_email_html(otp_code, name),
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(BREVO_API_URL, json=payload, headers=headers)
            
            if response.status_code in (200, 201, 202):
                logger.info(f"Successfully dispatched OTP email via Brevo to {to_email}.")
                return True
            else:
                logger.error(
                    f"Brevo API error ({response.status_code}): {response.text}"
                )
                return False
    except Exception as e:
        logger.error(f"Failed to send email via Brevo to {to_email}: {e}")
        return False
