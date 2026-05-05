import jwt
import base64
import os
from dotenv import load_dotenv

load_dotenv()

def test_token_verification():
    token = os.getenv("AUTH_TOKEN")
    secret = os.getenv("SUPABASE_JWT_SECRET")
    
    print(f"Token: {token[:20]}...")
    print(f"Secret: {secret[:10]}...")

    potential_secrets = []
    
    # 1. Base64 decode
    try:
        missing_padding = len(secret) % 4
        secret_to_decode = secret + ('=' * (4 - missing_padding)) if missing_padding else secret
        potential_secrets.append(("Base64 Decoded", base64.b64decode(secret_to_decode)))
    except Exception as e:
        print(f"Failed to b64decode: {e}")
    
    # 2. Raw string
    potential_secrets.append(("Raw String", secret.encode('utf-8')))

    for name, s in potential_secrets:
        try:
            payload = jwt.decode(token, s, algorithms=["HS256"], options={"verify_aud": False})
            print(f"✅ SUCCESS with {name}!")
            print(f"Payload: {payload}")
            return
        except jwt.ExpiredSignatureError:
            print(f"❌ EXPIRED with {name}")
        except jwt.InvalidSignatureError:
            print(f"❌ INVALID SIGNATURE with {name}")
        except Exception as e:
            print(f"❌ ERROR with {name}: {e}")

if __name__ == "__main__":
    test_token_verification()
