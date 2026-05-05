import jwt
import os
import base64
from dotenv import load_dotenv

load_dotenv()

def test_jwks_logic():
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    
    print(f"🔗 Connecting to JWKS: {JWKS_URL}")
    
    try:
        client = jwt.PyJWKClient(JWKS_URL)
        jwks = client.get_jwk_set()
        print(f"✅ Successfully fetched JWKS!")
        print(f"Keys found: {len(jwks.keys)}")
        for key in jwks.keys:
            print(f" - ID: {key.key_id}, Algorithm: {key.algorithm}")
            
    except Exception as e:
        print(f"❌ Failed to fetch/parse JWKS: {e}")

if __name__ == "__main__":
    test_jwks_logic()
