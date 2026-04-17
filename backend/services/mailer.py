import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from ..core.utils import get_env_safe

logger = logging.getLogger(__name__)

class Mailer:
    """Service to handle email transmissions via SMTP."""
    
    def __init__(self):
        self.user = get_env_safe("EMAIL_USER")
        self.password = get_env_safe("EMAIL_PASS")
        self.server = "smtp.gmail.com"
        self.port = 465 # SSL
        
    def _is_configured(self):
        return bool(self.user and self.password)

    async def send_interview_invitation(self, candidate_name: str, candidate_email: str, scheduled_at: str, room_link: str):
        """Transmits a secure interview invitation. Async wrapper."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._send_sync, candidate_name, candidate_email, scheduled_at, room_link)

    def _send_sync(self, candidate_name: str, candidate_email: str, scheduled_at: str, room_link: str):
        """Internal synchronous SMTP transmission."""
        if not self._is_configured():
            logger.error("Mailer not configured. Check EMAIL_USER and EMAIL_PASS.")
            raise Exception("Email service configuration incomplete.")

        try:
            # Format Date
            try:
                dt = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
                formatted_date = dt.strftime("%B %d, %Y at %I:%M %p")
            except:
                formatted_date = scheduled_at
            
            # Create Message
            msg = MIMEMultipart()
            msg['From'] = f"Integra Pro <{self.user}>"
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

            # Send
            with smtplib.SMTP_SSL(self.server, self.port) as server:
                server.login(self.user, self.password)
                server.send_message(msg)
            
            logger.info(f"Invitation sent to {candidate_email}")
            return {"status": "success", "id": "SMTP_SUCCESS"}
            
        except Exception as e:
            logger.error(f"Mailer failure: {e}")
            raise e

