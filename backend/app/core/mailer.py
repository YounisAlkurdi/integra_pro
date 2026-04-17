import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..utils import get_env_safe
from datetime import datetime

# --- Configuration ---
EMAIL_USER = get_env_safe("EMAIL_USER")
EMAIL_PASS = get_env_safe("EMAIL_PASS")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465 # SSL Port

def send_interview_invitation(candidate_name, candidate_email, scheduled_at, room_link):
    """
    Transmits a secure neural link invitation via Gmail SMTP (SSL).
    """
    if not EMAIL_USER or not EMAIL_PASS:
        print("MAILER_ERROR: Email credentials missing in .env")
        raise Exception("System offline: Email configuration incomplete.")

    try:
        # Format the date for the email
        dt = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
        formatted_date = dt.strftime("%B %d, %Y at %I:%M %p")
        
        # Create Message
        msg = MIMEMultipart()
        msg['From'] = f"Integra Pro <{EMAIL_USER}>"
        msg['To'] = candidate_email
        msg['Subject'] = f"Secure Interview Invitation: {candidate_name}"

        # HTML Content
        html_body = f"""
        <html>
            <body style="margin: 0; padding: 0; background-color: #0B0E11;">
                <div style="font-family: 'Inter', sans-serif; background-color: #0B0E11; color: #ffffff; padding: 40px; border-radius: 20px; border: 1px solid #22D3EE; max-width: 600px; margin: 20px auto;">
                    <h2 style="color: #22D3EE; text-transform: uppercase; letter-spacing: 2px; margin-top: 0;">Neural Link Established</h2>
                    <p style="color: rgba(255,255,255,0.6); line-height: 1.6;">A secure interview session has been scheduled for your identity within the Integra node.</p>
                    
                    <div style="background: rgba(255,255,255,0.05); padding: 20px; border-radius: 12px; margin: 20px 0; border: 1px solid rgba(34, 211, 238, 0.1);">
                        <p style="margin: 5px 0;"><strong>Candidate:</strong> {candidate_name}</p>
                        <p style="margin: 5px 0;"><strong>Scheduled Time:</strong> {formatted_date}</p>
                    </div>

                    <p style="margin-bottom: 30px; color: rgba(255,255,255,0.8);">Access the secure synchronization node via the following tactical link:</p>
                    
                    <div style="text-align: center;">
                        <a href="{room_link}" style="background-color: #22D3EE; color: #0B0E11; padding: 15px 35px; border-radius: 10px; text-decoration: none; font-weight: bold; display: inline-block; text-transform: uppercase; letter-spacing: 1px; box-shadow: 0 4px 15px rgba(34, 211, 238, 0.3);">
                            Join Secure Session
                        </a>
                    </div>
                    
                    <p style="margin-top: 40px; font-size: 10px; color: rgba(255,255,255,0.3); font-family: monospace; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 20px; text-align: center;">
                        SYSTEM_ID: INTEGRA_CORE_V1 | PROTOCOL: SECURE_NEURAL_LINK | ENCRYPTION: AES-256
                    </p>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))

        # Connect and Send using SSL
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        
        print(f"MAILER_SYNC: Invitation transmitted to {candidate_email}")
        return {"id": "SMTP_SUCCESS"}
        
    except Exception as e:
        print(f"MAILER_CRITICAL_FAILURE: {str(e)}")
        raise e
