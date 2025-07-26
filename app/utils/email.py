from mailjet_rest import Client
from app.models.settings import Settings
from flask import url_for
from datetime import datetime
import os
from flask import render_template

def get_mailjet_client():
    """Get configured Mailjet client or None"""
    try:
        # Use get_email_config to ensure encrypted values are used
        email_config = Settings.get_email_config()
        api_key = email_config.get('api_key')
        api_secret = email_config.get('api_secret')
        if not api_key or not api_secret:
            return None
        return Client(auth=(api_key, api_secret), version='v3.1')
    except Exception as e:
        print(f"Mailjet client error: {e}")
        return None

def send_share_notification(file_share):
    """Send file share notification email"""
    try:
        client = get_mailjet_client()
        if not client:
            return False
        from_email = Settings.get('mailjet_from_email', 'noreply@example.com')
        from_name = Settings.get('mailjet_from_name', 'Secure File Share')
        download_url = url_for('main.download_page', token=file_share.token, _external=True)
        try:
            if hasattr(file_share, 'expires_at') and file_share.expires_at:
                import pytz
                nz_tz = pytz.timezone('Pacific/Auckland')
                nz_time = file_share.expires_at.replace(tzinfo=pytz.UTC).astimezone(nz_tz)
                expires_str = nz_time.strftime('%Y-%m-%d %I:%M %p NZST')
            else:
                expires_str = 'Not set'
        except Exception as e:
            print(f"Error formatting expiry time: {e}")
            expires_str = 'Not set'
        # Render the HTML email template
        html_body = render_template(
            'email/share_notification.html',
            token=file_share.token,
            file_count=len(file_share.files),
            expires_str=expires_str,
            download_url=download_url
        )
        data = {
            'Messages': [
                {
                    "From": {
                        "Email": from_email,
                        "Name": from_name
                    },
                    "To": [
                        {
                            "Email": file_share.recipient_email,
                            "Name": file_share.recipient_email
                        }
                    ],
                    "Subject": "Secure Files Shared With You",
                    "TextPart": f"You have received secure file share. Download Token: {file_share.token} Download URL: {download_url} Files: {len(file_share.files)} file(s) Expires: {expires_str}",
                    "HTMLPart": html_body
                }
            ]
        }
        result = client.send.create(data=data)
        return result.status_code == 200
    except Exception as e:
        print(f"Email send error: {e}")
        return False

def send_test_email(test_email):
    """Send test email"""
    try:

        client = get_mailjet_client()
        if not client:
            return False

        from_email = Settings.get('mailjet_from_email', 'noreply@example.com')
        from_name = Settings.get('mailjet_from_name', 'Secure File Share')

        data = {
            'Messages': [
                {
                    "From": {
                        "Email": from_email,
                        "Name": from_name
                    },
                    "To": [
                        {
                            "Email": test_email,
                            "Name": test_email
                        }
                    ],
                    "Subject": "Test Email - Secure File Share",
                    "TextPart": "This is a test email from your Secure File Share system. Email configuration is working correctly!",
                    "HTMLPart": "<h2>Test Email</h2><p>This is a test email from your Secure File Share system.</p><p><strong>Email configuration is working correctly!</strong></p>"
                }
            ]
        }

        result = client.send.create(data=data)
        return result.status_code == 200
    except Exception as e:
        print(f"Test email error: {e}")
        return False
