import os
import json
from flask import Flask, jsonify, send_from_directory, request
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__, static_folder='.', template_folder='.')
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def get_drive_service():
    # 1. Check standard Render Secret File location
    secret_path = "/etc/secrets/service_account.json"
    
    # 2. Check local project directory
    local_path = os.path.join(BASE_DIR, "service_account.json")
    
    # 3. Check environment variable string
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

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(BASE_DIR, filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
