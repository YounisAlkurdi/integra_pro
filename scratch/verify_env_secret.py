import jwt
import os
import base64
from dotenv import load_dotenv

load_dotenv()

def verify_anon_key():
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    secret = os.getenv("SUPABASE_JWT_SECRET")
    
    print(f"Anon Key: {anon_key[:20]}...")
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
            payload = jwt.decode(anon_key, s, algorithms=["HS256"], options={"verify_aud": False})
            print(f"✅ SUCCESS verifying ANON KEY with {name}!")
            return True
        except jwt.InvalidSignatureError:
            print(f"❌ INVALID SIGNATURE for ANON KEY with {name}")
        except Exception as e:
            print(f"❌ ERROR for ANON KEY with {name}: {e}")
    
    return False

if __name__ == "__main__":
    verify_anon_key()
