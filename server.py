import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_drive_service():
    # 1. Check standard Render Secret File location
    secret_path = "/etc/secrets/service_account.json"
    
    # 2. Check local project directory
    local_path = os.path.join(os.path.dirname(__file__), "service_account.json")
    
    # 3. Check environment variable string (if pasted directly)
    env_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

    creds = None
    
    if os.path.exists(secret_path):
        creds = service_account.Credentials.from_service_account_file(
            secret_path, scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
    elif os.path.exists(local_path):
        creds = service_account.Credentials.from_service_account_file(
            local_path, scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
    elif env_json:
        info = json.loads(env_json)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
    else:
        raise FileNotFoundError(
            "Service account key not found in /etc/secrets/, project root, or environment variables."
        )

    return build("drive", "v3", credentials=creds)
