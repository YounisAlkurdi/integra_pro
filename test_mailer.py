from mailer import send_interview_invitation
import os
from dotenv import load_dotenv

load_dotenv()

def test_invitation():
    print("--- MAILER TEST PROTOCOL ---")
    
    # Configuration check
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    
    if not email_user or "your_email" in email_user:
        print("ERROR: Please update EMAIL_USER in .env with your real Gmail.")
        return
        
    if not email_pass or "your_app_password" in email_pass:
        print("ERROR: Please update EMAIL_PASS in .env with your 16-character App Password.")
        print("Hint: Go to Google Account Security -> 2-Step Verification -> App Passwords.")
        return

    test_email = input(f"Enter recipient email to test (default: {email_user}): ") or email_user
    
    print(f"Attempting to synchronize via {email_user}...")
    
    try:
        send_interview_invitation(
            candidate_name="Test Candidate",
            candidate_email=test_email,
            scheduled_at="2026-04-11T18:00:00Z",
            room_link="https://integra-pro-puce.vercel.app/test-room"
        )
        print("\nSUCCESS: Neural Link Invitation Transmitted!")
        print(f"Check the inbox (or spam) of: {test_email}")
    except Exception as e:
        print(f"\nCRITICAL FAILURE: {str(e)}")
        print("\nTroubleshooting Tips:")
        print("1. Ensure 2-Step Verification is ON in Google.")
        print("2. Use a 16-character 'App Password', NOT your regular login password.")
        print("3. Check if your internet allows SMTP (Port 587).")

if __name__ == "__main__":
    test_invitation()
