import jwt
import base64

# From .env
secret = "xAvtmlf3RhV1ldfK++iYtz9Z2ZHOyxCdJyOIysqaPLuf9K6brTTLUmhFR+JfC3Xbquf1AzEPf/SHq7i5kKbk+g=="
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxODA4OTc2OTU2LCJzdWIiOiJkNjIyODUzZS05M2M1LTQ3YWYtOGY4NC0xNTcxN2UzZjM2YmQiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIn0sInVzZXJfbWV0YWRhdGEiOnt9fQ.cDUxbJX6C-70TCPORC5BeliXIpJHAd7PyQJ21KY80e8"

def test_verify(s, t):
    print(f"Testing with secret: {s[:10]}...")
    try:
        # 1. Try as raw string
        payload = jwt.decode(t, s, algorithms=["HS256"], options={"verify_aud": False})
        print("✅ Verified as RAW STRING")
        return True
    except Exception as e:
        print(f"❌ Failed as RAW STRING: {e}")

    try:
        # 2. Try as decoded base64
        missing_padding = len(s) % 4
        s_padded = s + ('=' * (4 - missing_padding)) if missing_padding else s
        decoded = base64.b64decode(s_padded)
        payload = jwt.decode(t, decoded, algorithms=["HS256"], options={"verify_aud": False})
        print("✅ Verified as DECODED BASE64")
        return True
    except Exception as e:
        print(f"❌ Failed as DECODED BASE64: {e}")
    
    return False

test_verify(secret, token)
