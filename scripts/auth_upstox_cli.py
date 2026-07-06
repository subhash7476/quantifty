import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import requests
from urllib.parse import urlencode, parse_qs, urlparse
from core.auth.credentials import credentials

def exchange_code(code):
    api_key = credentials.get("api_key")
    api_secret = credentials.get("api_secret")
    redirect_uri = credentials.get("redirect_uri", "http://127.0.0.1:5000/ops/callback/upstox")

    print("Exchanging auth code for access token...")
    url = "https://api.upstox.com/v2/login/authorization/token"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "code": code,
        "client_id": api_key,
        "client_secret": api_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    resp = requests.post(url, headers=headers, data=data)
    resp.raise_for_status()
    token_data = resp.json()
    credentials.save(token_data)
    print("Token saved successfully!")
    print(f"  User ID:     {token_data.get('user_id', 'N/A')}")
    print(f"  User Name:   {token_data.get('user_name', 'N/A')}")
    print(f"  Token Type:  {token_data.get('token_type', 'N/A')}")
    print(f"  Expires In:  {token_data.get('expires_in', 'N/A')} seconds")

def main():
    if len(sys.argv) > 1:
        code = sys.argv[1]
        exchange_code(code)
        return

    api_key = credentials.get("api_key")
    redirect_uri = credentials.get("redirect_uri", "http://127.0.0.1:5000/ops/callback/upstox")

    if not api_key:
        print("Error: api_key not found in config/credentials.json")
        sys.exit(1)

    params = {
        "response_type": "code",
        "client_id": api_key,
        "redirect_uri": redirect_uri,
    }
    auth_url = f"https://api.upstox.com/v2/login/authorization/dialog?{urlencode(params)}"

    print("=" * 60)
    print("UPSTOX OAUTH TOKEN REFRESH")
    print("=" * 60)
    print(f"\n1. Open this URL in your browser:\n   {auth_url}\n")
    print(f"2. Log in to Upstox.")
    print(f"3. After login, copy the `code` parameter from the redirect URL.")
    print(f"4. Run: python scripts/auth_upstox_cli.py YOUR_CODE\n")

if __name__ == "__main__":
    main()
