import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, 'backend'))

from backend.utils import get_env_safe

print("Checking environment variables...")
stripe_pk = get_env_safe("STRIPE_PUBLISHABLE_KEY")
stripe_sk = get_env_safe("STRIPE_SECRET_KEY")
supabase_url = get_env_safe("SUPABASE_URL")
supabase_key = get_env_safe("SUPABASE_SERVICE_ROLE_KEY")

print(f"STRIPE_PUBLISHABLE_KEY: {'[SET]' if stripe_pk else '[MISSING]'}")
print(f"STRIPE_SECRET_KEY: {'[SET]' if stripe_sk else '[MISSING]'}")
print(f"SUPABASE_URL: {'[SET]' if supabase_url else '[MISSING]'}")
print(f"SUPABASE_SERVICE_ROLE_KEY: {'[SET]' if supabase_key else '[MISSING]'}")

import stripe
stripe.api_key = stripe_sk
try:
    balance = stripe.Balance.retrieve()
    print("Stripe Connection: [SUCCESS]")
except Exception as e:
    print(f"Stripe Connection: [FAILED] - {e}")

import urllib.request
import json
try:
    url = f"{supabase_url}/rest/v1/invoices?limit=1"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        content = resp.read()
        print("Supabase Connection: [SUCCESS]")
except Exception as e:
    print(f"Supabase Connection: [FAILED] - {e}")
