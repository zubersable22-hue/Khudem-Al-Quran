import os
import json
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

app = Flask(__name__)
CORS(app)

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
DRIVE_ROOT_FOLDER_ID = '1auFuV06S9Cx6wbUNFShdEzxke334L4zM'

def get_drive_service():
    service_account_info = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    
    if service_account_info:
        creds_dict = json.loads(service_account_info)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
    elif os.path.exists('service_account.json'):
        creds = service_account.Credentials.from_service_account_file(
            'service_account.json', scopes=SCOPES
        )
    else:
        raise FileNotFoundError("Google Service Account credentials not found.")

    return build('drive', 'v3', credentials=creds)

@app.route('/')
def home():
    return jsonify({
        "status": "success",
        "message": "Khudem Al Quran API is running"
    })

@app.route('/api/surahs', methods=['GET'])
def get_surahs():
    surahs = [
        {"id": 1, "name": "Al-Fatiha", "ayahs": 7},
        {"id": 2, "name": "Al-Baqarah", "ayahs": 286},
    ]
    return jsonify(surahs)

@app.route('/api/ayah_count', methods=['GET'])
def get_ayah_count():
    surah = request.args.get('surah', 1, type=int)
    ayah_counts = {1: 7, 2: 286, 3: 200, 4: 176, 5: 120, 6: 165, 7: 206, 8: 75, 9: 129, 10: 109, 112: 4}
    count = ayah_counts.get(surah, 1)
    return jsonify({"surah": surah, "ayah_count": count})

@app.route('/api/opening', methods=['GET'])
def get_opening():
    return jsonify({"status": "success", "message": "App ready"})

@app.route('/audio', methods=['GET'])
def get_audio():
    qari = request.args.get('qari', 'Abdul_Basit_Mujawwad')
    surah = request.args.get('surah', 1, type=int)
    ayah = request.args.get('ayah', 1, type=int)
    
    try:
        service = get_drive_service()
        file_path = f"{qari}/Surah_{surah:03d}/ayah_{ayah:03d}.mp3"
        query = f"name='{file_path}' and parents='{DRIVE_ROOT_FOLDER_ID}'"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)', pageSize=1).execute()
        items = results.get('files', [])
        
        if not items:
            return jsonify({"status": "error", "message": f"Audio not found"}), 404
        
        file_id = items[0]['id']
        request_obj = service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request_obj)
        done = False
        
        while not done:
            status, done = downloader.next_chunk()
        
        file.seek(0)
        return send_file(file, mimetype='audio/mpeg', as_attachment=False, download_name='audio.mp3')
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/taawooz-audio', methods=['GET'])
def get_taawooz():
    try:
        service = get_drive_service()
        query = f"name='taawooz.mp3' and parents='{DRIVE_ROOT_FOLDER_ID}'"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)', pageSize=1).execute()
        items = results.get('files', [])
        
        if not items:
            return jsonify({"status": "error", "message": "Taawooz not found"}), 404
        
        file_id = items[0]['id']
        request_obj = service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request_obj)
        done = False
        
        while not done:
            status, done = downloader.next_chunk()
        
        file.seek(0)
        return send_file(file, mimetype='audio/mpeg', as_attachment=False, download_name='taawooz.mp3')
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)