import os
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)

# Enable CORS for all routes (allows mobile apps / web frontends to connect)
CORS(app)

# ---------------------------------------------------------
# Root / Health Check Route
# ---------------------------------------------------------
@app.route('/')
def home():
    return jsonify({
        "status": "success",
        "message": "Khudem Al Quran API is running"
    })

# ---------------------------------------------------------
# Example API Routes (Modify or add your own endpoints here)
# ---------------------------------------------------------
@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "server": "online",
        "version": "1.0.0"
    })

# ---------------------------------------------------------
# Server Execution Configuration
# ---------------------------------------------------------
if __name__ == '__main__':
    # Render assigns dynamic ports via the PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
