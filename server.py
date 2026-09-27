import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------
# Google Drive Service Account Setup
# ---------------------------------------------------------
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    # 1. First check environment variable (Render production)
    service_account_info = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    
    if service_account_info:
        creds_dict = json.loads(service_account_info)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
    # 2. Fall back to local file if environment variable is not present
    elif os.path.exists('service_account.json'):
        creds = service_account.Credentials.from_service_account_file(
            'service_account.json', scopes=SCOPES
        )
    else:
        raise FileNotFoundError("Google Service Account credentials not found.")

    return build('drive', 'v3', credentials=creds)

# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------
@app.route('/')
def home():
    return jsonify({
        "status": "success",
        "message": "Khudem Al Quran API is running"
    })

# Route to test Google Drive access & list files/folders
@app.route('/api/files', methods=['GET'])
def list_files():
    try:
        service = get_drive_service()
        # Query up to 10 files accessible by the service account
        results = service.files().list(
            pageSize=10, 
            fields="nextPageToken, files(id, name, mimeType)"
        ).execute()
        items = results.get('files', [])

        return jsonify({
            "status": "success",
            "count": len(items),
            "files": items
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
