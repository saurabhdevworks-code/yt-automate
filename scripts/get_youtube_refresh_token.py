#!/usr/bin/env python3
# Run locally once to obtain OAuth values for GitHub Actions secrets.
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-secrets", required=True)
    args = parser.parse_args()
    flow = InstalledAppFlow.from_client_secrets_file(
        args.client_secrets, scopes=["https://www.googleapis.com/auth/youtube.upload"])
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    print("\nStore these as GitHub Actions secrets; never commit them:")
    print("YOUTUBE_CLIENT_ID=" + str(creds.client_id))
    print("YOUTUBE_CLIENT_SECRET=" + str(creds.client_secret))
    print("YOUTUBE_REFRESH_TOKEN=" + str(creds.refresh_token or "No refresh token returned; rerun consent flow"))
if __name__ == "__main__":
    main()
