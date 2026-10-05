"""
The Holy Quran App - Qari Recitations (Hifz Made Easy)
Reads audio from Google Drive (via a service account + a pre-built manifest.json
index) instead of local ZIPs, so this can run on a hosted server that has no
access to anyone's D: drive.
Auto-plays Taawooz and Bismillah on first click anywhere in the app.
"""

import os
import re
import io
import json
import threading
import mimetypes
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ---------------------------------------------------------------------------
# Static assets (PNGs, background/button images) are bundled INTO this repo,
# so they're just relative folders next to this script.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHAPTER_NAMES_ROOT = os.path.join(BASE_DIR, "chapter_names")
STATIC_ROOT = os.path.join(BASE_DIR, "static")
MANIFEST_PATH = os.path.join(BASE_DIR, "manifest.json")

# The recitation audio itself lives on Google Drive. This is the JSON key file
# for the service account we shared the Drive folder with (Viewer access).
# On Render this is a "Secret File" mounted at /etc/secrets/<filename>.
SERVICE_ACCOUNT_FILE = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_FILE", "/etc/secrets/service_account.json"
)
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Render assigns the port at runtime via $PORT; 8787 is only for local testing.
PORT = int(os.environ.get("PORT", 8787))
AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".ogg", ".aac", ".opus"}
mimetypes.add_type("audio/ogg", ".opus")

# File stems for standalone opening audio files located directly in the Drive
# QuranDownload root folder.
TAAWOOZ_FILE_STEM = "009000"
BISMILLAH_FILE_STEM = "001001"

TEST_SURAHS = {
    1: "Surah Al-Fatihah", 2: "Surah Al-Baqarah", 3: "Surah Aal-E-Imran", 4: "Surah An-Nisa",
    5: "Surah Al-Ma'idah", 6: "Surah Al-An'am", 7: "Surah Al-A'raf", 8: "Surah Al-Anfal",
    9: "Surah At-Tawbah", 10: "Surah Yunus", 11: "Surah Hud", 12: "Surah Yusuf",
    13: "Surah Ar-Ra'd", 14: "Surah Ibrahim", 15: "Surah Al-Hijr", 16: "Surah An-Nahl",
    17: "Surah Al-Isra", 18: "Surah Al-Kahf", 19: "Surah Maryam", 20: "Surah Ta-Ha",
    21: "Surah Al-Anbiya", 22: "Surah Al-Hajj", 23: "Surah Al-Mu'minun", 24: "Surah An-Nur",
    25: "Surah Al-Furqan", 26: "Surah Ash-Shu'ara", 27: "Surah An-Naml", 28: "Surah Al-Qasas",
    29: "Surah Al-Ankabut", 30: "Surah Ar-Rum", 31: "Surah Luqman", 32: "Surah As-Sajdah",
    33: "Surah Al-Ahzab", 34: "Surah Saba", 35: "Surah Fatir", 36: "Surah Ya-Sin",
    37: "Surah As-Saffat", 38: "Surah Sad", 39: "Surah Az-Zumar", 40: "Surah Ghafir",
    41: "Surah Fussilat", 42: "Surah Ash-Shura", 43: "Surah Az-Zukhruf", 44: "Surah Ad-Dukhan",
    45: "Surah Al-Jathiyah", 46: "Surah Al-Ahqaf", 47: "Surah Muhammad", 48: "Surah Al-Fath",
    49: "Surah Al-Hujurat", 50: "Surah Qaf", 51: "Surah Adh-Dhariyat", 52: "Surah At-Tur",
    53: "Surah An-Najm", 54: "Surah Al-Qamar", 55: "Surah Ar-Rahman", 56: "Surah Al-Waqi'ah",
    57: "Surah Al-Hadid", 58: "Surah Al-Mujadilah", 59: "Surah Al-Hashr", 60: "Surah Al-Mumtahanah",
    61: "Surah As-Saff", 62: "Surah Al-Jumu'ah", 63: "Surah Al-Munafiqun", 64: "Surah At-Taghabun",
    65: "Surah At-Talaq", 66: "Surah At-Tahrim", 67: "Surah Al-Mulk", 68: "Surah Al-Qalam",
    69: "Surah Al-Haqqah", 70: "Surah Al-Ma'arij", 71: "Surah Nuh", 72: "Surah Al-Jinn",
    73: "Surah Al-Muzzammil", 74: "Surah Al-Muddaththir", 75: "Surah Al-Qiyamah", 76: "Surah Al-Insan",
    77: "Surah Al-Mursalat", 78: "Surah An-Naba", 79: "Surah An-Nazi'at", 80: "Surah Abasa",
    81: "Surah At-Takwir", 82: "Surah Al-Infitar", 83: "Surah Al-Mutaffifin", 84: "Surah Al-Inshiqaq",
    85: "Surah Al-Buruj", 86: "Surah At-Tariq", 87: "Surah Al-A'la", 88: "Surah Al-Ghashiyah",
    89: "Surah Al-Fajr", 90: "Surah Al-Balad", 91: "Surah Ash-Shams", 92: "Surah Al-Layl",
    93: "Surah Ad-Duha", 94: "Surah Ash-Sharh", 95: "Surah At-Tin", 96: "Surah Al-Alaq",
    97: "Surah Al-Qadr", 98: "Surah Al-Bayyinah", 99: "Surah Az-Zalzalah", 100: "Surah Al-Adiyat",
    101: "Surah Al-Qari'ah", 102: "Surah At-Takathur", 103: "Surah Al-Asr", 104: "Surah Al-Humazah",
    105: "Surah Al-Fil", 106: "Surah Quraysh", 107: "Surah Al-Ma'un", 108: "Surah Al-Kawthar",
    109: "Surah Al-Kafirun", 110: "Surah An-Nasr", 111: "Surah Al-Masad", 112: "Surah Al-Ikhlas",
    113: "Surah Al-Falaq", 114: "Surah An-Nas",
}
JUZ_LABEL = "Juz 1 - 30"

_BITRATE_SUFFIX_RE = re.compile(r"_\d+kbps$", re.IGNORECASE)


def display_qari_name(folder_name):
    """Formats folder names into a respectful title like 'The Qari Abdul Basit'."""
    name = _BITRATE_SUFFIX_RE.sub("", folder_name)
    cleaned = name.replace("_", " ").strip()
    return f"The Qari {cleaned}"



# ---------------------------------------------------------------------------
# manifest.json is a pre-built index of { qari -> surah -> ayah -> drive_file_id }
# produced by build_manifest.py (run locally, once, whenever the Drive library
# changes). We load it once at startup instead of hitting the Drive API just to
# list folders on every request.
_MANIFEST = None
_MANIFEST_LOCK = threading.Lock()


def load_manifest():
    global _MANIFEST
    with _MANIFEST_LOCK:
        if _MANIFEST is None:
            if not os.path.isfile(MANIFEST_PATH):
                raise FileNotFoundError(
                    f"manifest.json not found at {MANIFEST_PATH}. "
                    f"Run build_manifest.py first and commit the result."
                )
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                _MANIFEST = json.load(f)
        return _MANIFEST


def list_qari_folders():
    manifest = load_manifest()
    return sorted(manifest.get("qaris", {}).keys())


def find_standalone_audio(stem):
    """Returns a Drive file_id for a standalone opening clip, or None."""
    manifest = load_manifest()
    if stem == TAAWOOZ_FILE_STEM:
        return manifest.get("taawooz_file_id")
    if stem == BISMILLAH_FILE_STEM:
        return manifest.get("bismillah_file_id")
    return None


def list_surah_files(qari_folder_name, surah_number):
    """Returns [{"ayah": n}, ...] for every ayah available for this qari+surah,
    sorted by ayah number, based on manifest.json (no network call)."""
    manifest = load_manifest()
    surah_map = manifest.get("qaris", {}).get(qari_folder_name, {}).get(str(int(surah_number)), {})
    ayah_numbers = sorted(int(a) for a in surah_map.keys())
    return [{"ayah": a} for a in ayah_numbers]


def audio_file_id(qari_folder_name, surah_number, ayah_number):
    """Looks up the Drive file_id for one specific qari+surah+ayah."""
    manifest = load_manifest()
    surah_map = manifest.get("qaris", {}).get(qari_folder_name, {}).get(str(int(surah_number)), {})
    return surah_map.get(str(int(ayah_number)))


# ---------------------------------------------------------------------------
# Google Drive access: authenticate once, then download individual small
# audio files on demand. Because every file here is tiny (tens of KB), we also
# keep a small in-memory LRU cache so repeat plays of the same ayah (very
# common — Al-Fatiha ayah 1 gets hit constantly) don't re-hit the Drive API.
_drive_service = None
_drive_service_lock = threading.Lock()


def get_drive_service():
    global _drive_service
    if _drive_service is None:
        with _drive_service_lock:
            if _drive_service is None:
                if not os.path.isfile(SERVICE_ACCOUNT_FILE):
                    raise FileNotFoundError(
                        f"Service account key not found at {SERVICE_ACCOUNT_FILE}. "
                        f"Set GOOGLE_SERVICE_ACCOUNT_FILE or add the Render Secret File."
                    )
                creds = service_account.Credentials.from_service_account_file(
                    SERVICE_ACCOUNT_FILE, scopes=DRIVE_SCOPES
                )
                _drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return _drive_service


_AUDIO_CACHE = OrderedDict()
_AUDIO_CACHE_MAX_ITEMS = 500  # ~500 opus files x ~40KB avg ~= 20MB, safe for free tier RAM
_audio_cache_lock = threading.Lock()


def fetch_drive_file_bytes(file_id):
    with _audio_cache_lock:
        cached = _AUDIO_CACHE.get(file_id)
        if cached is not None:
            _AUDIO_CACHE.move_to_end(file_id)
            return cached

    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    data = buf.getvalue()

    with _audio_cache_lock:
        _AUDIO_CACHE[file_id] = data
        _AUDIO_CACHE.move_to_end(file_id)
        while len(_AUDIO_CACHE) > _AUDIO_CACHE_MAX_ITEMS:
            _AUDIO_CACHE.popitem(last=False)
    return data


_CHAPTER_INDEX = None
_CHAPTER_INDEX_LOCK = threading.Lock()


def _build_chapter_index():
    """Scan chapter_names (any subfolder, any letter-case) once and map
    surah number -> PNG path. Files look like '1- Surah Al-Fatihah.png'."""
    index = {}
    root = CHAPTER_NAMES_ROOT
    if not os.path.isdir(root):
        # Linux is case-sensitive: try to find the folder ignoring case.
        for name in os.listdir(BASE_DIR):
            if name.lower().replace(" ", "_") == "chapter_names" and os.path.isdir(os.path.join(BASE_DIR, name)):
                root = os.path.join(BASE_DIR, name)
                break
        else:
            return index
    num_re = re.compile(r"^\s*0*(\d{1,3})(?!\d)")
    for dirpath, _dirs, files in os.walk(root):
        for fn in sorted(files):
            if not fn.lower().endswith(".png"):
                continue
            m = num_re.match(fn)
            if m:
                index.setdefault(int(m.group(1)), os.path.join(dirpath, fn))
    return index


def find_chapter_name_image(surah_number):
    global _CHAPTER_INDEX
    try:
        n = int(surah_number)
    except (TypeError, ValueError):
        return None
    with _CHAPTER_INDEX_LOCK:
        if _CHAPTER_INDEX is None:
            _CHAPTER_INDEX = _build_chapter_index()
        return _CHAPTER_INDEX.get(n)

_JUZ_INDEX = None
_JUZ_INDEX_LOCK = threading.Lock()


def _build_juz_index():
    """Juz name PNGs live in the SAME folder as the chapter names
    (chapter_names, any subfolder, any letter-case). Files look like
    'juz1.png' ... 'juz30.png'. Chapter files (which start with the surah
    number) are never matched because only names starting with 'juz' count."""
    index = {}
    root = CHAPTER_NAMES_ROOT
    if not os.path.isdir(root):
        for name in os.listdir(BASE_DIR):
            if name.lower().replace(" ", "_") == "chapter_names" and os.path.isdir(os.path.join(BASE_DIR, name)):
                root = os.path.join(BASE_DIR, name)
                break
        else:
            return index
    juz_re = re.compile(r"^\s*juz\s*[_-]?\s*0*(\d{1,2})(?!\d)", re.IGNORECASE)
    for dirpath, _dirs, files in os.walk(root):
        for fn in sorted(files):
            if not fn.lower().endswith(".png"):
                continue
            m = juz_re.match(fn)
            if m and 1 <= int(m.group(1)) <= 30:
                index.setdefault(int(m.group(1)), os.path.join(dirpath, fn))
    return index


def find_juz_name_image(juz_number):
    global _JUZ_INDEX
    try:
        n = int(juz_number)
    except (TypeError, ValueError):
        return None
    with _JUZ_INDEX_LOCK:
        if _JUZ_INDEX is None:
            _JUZ_INDEX = _build_juz_index()
        return _JUZ_INDEX.get(n)

def safe_join(root, *parts):
    target = os.path.normpath(os.path.join(root, *parts))
    root_norm = os.path.normpath(root)
    if not target.startswith(root_norm):
        return None
    return target


# ---------------------------------------------------------------------------
INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<title>The Qari - Memorize With Perfection</title>
<script>document.documentElement.classList.add('fit-pending');</script>
<style>
  * { 
    box-sizing: border-box; 
    margin: 0; 
    padding: 0; 
  }
  
  html, body {
    width: 100%;
    height: 100%;
    min-height: 100vh;
    background: #2b3a1a;
    font-family: "Georgia", "Times New Roman", serif;
    margin: 0;
    padding: 0;
    overflow-x: hidden;
  }

  body { 
    display: flex; 
    justify-content: center; 
    align-items: center; 
    background-color: #2b3a1a;
  }
  
  .app-container { 
    width: 100%;
    max-width: 500px;
    min-height: 100vh;
    min-height: 100dvh;
    background: #ede6d6 url('/static/background_2.jpg') no-repeat center center;
    background-size: cover;
    padding: calc(220px - 9mm) 20px 60px 20px;
    display: flex; 
    flex-direction: column; 
    justify-content: flex-start; 
    position: relative; 
    margin: 0 auto;
    box-shadow: 0 0 20px rgba(0,0,0,0.5);
  }

  @media (max-width: 600px) {
    .app-container {
      width: 100vw !important;
      max-width: 100vw !important;
      min-height: 100vh;
      min-height: 100dvh;
      padding-top: calc(52vw - 9mm);
      padding-bottom: 10vw;
      padding-left: 16px;
      padding-right: 16px;
      box-shadow: none;
      border-radius: 0;
    }
  }

  /* Wrapper around everything except the footer tagline. On desktop it is
     invisible (display: contents) so the layout there is untouched. */
  #stageMain { display: contents; }

  /* ===== Phones (<= 600px): locked, full-screen, seamless =====
     - The page never scrolls or bounces; the card is pinned to the screen.
     - The design is drawn once at a 412px reference width and scaled to fit
       any phone, so proportions are identical everywhere.
     - Content is anchored to the background artwork (header art at the top,
       tagline box at the bottom), so text and artwork always line up.
     The numbers used for anchoring live in fitStage() in the script below. */
  @media (max-width: 600px) {
    html, body {
      position: fixed; inset: 0;
      width: 100%; height: 100%; min-height: 0;
      overflow: hidden;
      overscroll-behavior: none;
      touch-action: manipulation;
      -webkit-tap-highlight-color: transparent;
      -webkit-text-size-adjust: 100%;
      background-color: #abc38b;
    }
    body { display: block; }
    .app-container {
      position: fixed; inset: 0;
      width: 100% !important; max-width: none !important;
      height: 100%; min-height: 0 !important;
      margin: 0; padding: 0 !important;
      display: block;
      overflow: hidden;
      box-shadow: none; border-radius: 0;
    }
    #stageMain {
      display: flex; flex-direction: column; justify-content: space-between;
      position: absolute; left: 0; top: 0;
      width: 412px; padding: 0 16px;
      transform-origin: 0 0;
    }
    .slot-footer-tagline {
      position: absolute !important; left: 0; top: 0;
      width: 380px !important; margin: 0 !important;
      transform-origin: 0 0;
    }
    .fit-pending #stageMain, .fit-pending .slot-footer-tagline { opacity: 0; }
  }

  .field { 
    margin-bottom: 8px; 
    position: relative;
    width: 100%;
  }

  .field label { 
    display: block; 
    color: #2b3a1a; 
    font-weight: 800; 
    font-size: 13px; 
    margin-bottom: 3px; 
    letter-spacing: 0.2px;
    text-align: center;
  }

  .field label.surah-label {
    margin-left: 0;
  }
  
  .select-wrapper { 
    position: relative; 
    width: 100%; 
    height: 42px;
    background: #ffffff url('/static/textarea_2.jpg') no-repeat center center;
    background-size: 100% 100%;
    border-radius: 21px;
    display: flex;
    align-items: center;
    padding: 0 12px;
    cursor: pointer;
  }

  .selected-display {
    width: 100%;
    font-size: 14px;
    font-weight: bold;
    color: #5a6324;
    padding-left: 8px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .custom-select-options {
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    max-height: 250px;
    overflow-y: auto;
    background: #fff8f0;
    border: 1px solid #c4bea8;
    border-radius: 12px;
    z-index: 1000;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    margin-top: 4px;
  }

  .custom-select-options.show {
    display: block;
  }

  .option-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 12px;
    border-bottom: 1px solid #f0ede6;
    cursor: pointer;
    font-size: 14px;
    font-weight: bold;
    color: #2b3a1a;
  }

  .option-item:last-child {
    border-bottom: none;
  }

  .option-item:hover {
    background-color: #e2ebd8;
  }

  .option-surah-name {
    flex: 1;
    text-align: left;
  }

  .option-arabic-img {
    height: 26px;
    max-width: 90px;
    object-fit: contain;
    margin: 0 10px;
  }

  .option-juz-img {
    height: 35.1px;   /* 26px + 35% */
    max-width: 112.5px;   /* 90px + 25% */
    object-fit: contain;
    margin: 0 4px 0 10px;
  }

  .option-surah-num {
    width: 30px;
    text-align: right;
    font-weight: 800;
    color: #5a6324;
  }

  select { 
    width: 100%; 
    height: 100%;
    background: transparent;
    border: none;
    outline: none;
    font-size: 14px; 
    font-weight: bold; 
    color: #5a6324; 
    appearance: none; 
    -webkit-appearance: none; 
    cursor: pointer;
    text-align: left;
    text-align-last: left;
    padding-left: 8px;
    padding-right: 0;
  }

  select option {
    color: #5a6324;
    font-weight: bold;
  }

  /* Ayah box only: text centred */
  #ayahSelect {
    text-align: center;
    text-align-last: center;
    padding-left: 0;
  }

  .surah-arabic-name { 
    position: absolute; 
    right: 48px; 
    top: 50%; 
    transform: translateY(-50%); 
    height: 24px; 
    max-width: 75px; 
    object-fit: contain; 
    pointer-events: none; 
  }

  /* Arabic Juz name: identical settings to .surah-arabic-name */
  .juz-arabic-name {
    position: absolute;
    right: 14px;
    top: 50%;
    transform: translateY(-50%);
    height: 32.4px;   /* 24px + 35% */
    max-width: 93.75px;   /* 75px + 25% */
    object-fit: contain;
    pointer-events: none;
    display: none;
  }

  /* Juz serial number at the far right, same look as .surah-arabic-num */
  .juz-arabic-num {
    position: absolute;
    right: 14px;
    top: 50%;
    transform: translateY(-50%);
    min-width: 28px;
    text-align: right;
    font-size: 14px;
    font-weight: 800;
    color: #5a6324;
    pointer-events: none;
  }

  /* Serial number shown at the far right, after the Arabic chapter name
     (same look as the number column in the Surah drop-down list). */
  .surah-arabic-num {
    position: absolute;
    right: 14px;
    top: 50%;
    transform: translateY(-50%);
    min-width: 28px;
    text-align: right;
    font-size: 14px;
    font-weight: 800;
    color: #5a6324;
    pointer-events: none;
  }

  .repeat-hint { 
    color: #3f6e1f; 
    font-weight: 900; 
    text-align: center; 
    font-size: 12px; 
    line-height: 1.2; 
    margin: 12px 0 6px 0; 
    text-transform: uppercase; 
    letter-spacing: 0.5px;
  }

  .grid3 { 
    display: grid; 
    grid-template-columns: 1fr 1fr 1fr; 
    gap: 8px; 
    width: 100%;
  }

  button.btn-big { 
    background: #e2ebd8 url('/static/bigbutton_2.png') no-repeat center center;
    background-size: 100% 100%;
    border: 1px solid #a8c298;
    border-radius: 8px;
    height: 60px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    outline: none;
    transition: transform 0.1s ease;
  }
  button.btn-big:active { transform: scale(0.96); }
  button.btn-big .big { font-size: 20px; font-weight: 900; color: #2c4416; line-height: 1; }
  button.btn-big .big-num { height: 26px; width: auto; max-width: 90%; display: block; margin: 0 auto; }
  button.btn-big .small { font-size: 9px; font-weight: 800; color: #2c4416; margin-top: 3px; letter-spacing: 0.5px; }

  button.btn-small { 
    background: #f0ede6 url('/static/smallbutton_2.png') no-repeat center center;
    background-size: 100% 100%;
    border: 1px solid #c4bea8;
    border-radius: 10px;
    height: 42px;
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    outline: none;
    transition: transform 0.1s ease;
  }
  button.btn-small:active { transform: scale(0.96); }
  button.btn-small .title { font-size: 11px; font-weight: 900; color: #2b3a1a; letter-spacing: 0.5px; }

  .nav-grid {
    margin-top: 8px;
    margin-bottom: 12px;
  }

  .status { 
    font-size: 11px; 
    color: #3f6e1f; 
    font-weight: bold;
    text-align: center; 
    min-height: 16px; 
    margin: 4px 0; 
  }

  /* --- Multilingual animated labels (English -> Arabic -> Urdu) ---
     Added on top of the existing layout; nothing above this point was
     changed. Each fade-slot cycles 3 stacked PNGs. Box size is driven by
     aspect-ratio (matched to each PNG set's own W:H) instead of a guessed
     fixed height, so it can't clip or spill into neighboring elements. */
  .fade-slot {
    position: relative;
    display: block;
    width: 100%;
    overflow: visible;
  }

  .fade-slot img {
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    width: auto;
    height: 100%;
    max-width: 100%;
    object-fit: contain;
    opacity: 0;
    animation-duration: 48s;
    animation-iteration-count: infinite;
  }

  /* 48s cycle = English 9s + 21s pause (English stays on screen, 30s in
     total), then Arabic 9s, then Urdu 9s, then it pauses on English again.
     Each language has its own keyframes below (0.5s fades). To change the
     pause, change the pause here AND the percentages in the 3 keyframes. */
  .fade-slot img:nth-child(1) { animation-name: langFadeEn; }
  .fade-slot img:nth-child(2) { animation-name: langFadeAr; }
  .fade-slot img:nth-child(3) { animation-name: langFadeUr; }

  /* Language sizing: English text PNGs -21%, Arabic + Urdu text PNGs +15%.
     Change these two numbers to fine-tune everything at once. */
  :root { --en-scale: 0.79; --ar-ur-scale: 1.15; }
  .fade-slot img:nth-child(1) { transform: translateX(-50%) scale(var(--en-scale)); }
  .fade-slot img:nth-child(2),
  .fade-slot img:nth-child(3) { transform: translateX(-50%) scale(var(--ar-ur-scale)); }

  /* English: visible 0s-30s (9s + 21s pause) */
  @keyframes langFadeEn {
    0% { opacity: 0; }
    1.04% { opacity: 1; }
    61.46% { opacity: 1; }
    62.5% { opacity: 0; }
    100% { opacity: 0; }
  }
  /* Arabic: visible 30s-39s */
  @keyframes langFadeAr {
    0%, 62.5% { opacity: 0; }
    63.54% { opacity: 1; }
    80.21% { opacity: 1; }
    81.25% { opacity: 0; }
    100% { opacity: 0; }
  }
  /* Urdu: visible 39s-48s */
  @keyframes langFadeUr {
    0%, 81.25% { opacity: 0; }
    82.29% { opacity: 1; }
    98.96% { opacity: 1; }
    100% { opacity: 0; }
  }

  /* Slot shapes, sized to match what each replaced text element used to
     occupy (.field label was ~13px text, .repeat-hint ~12px text, the
     button .small/.title text was 9-11px). Adjust the aspect-ratio on any
     one line if a given PNG set's real proportions differ. */
  .slot-field-label  { width: 65%; aspect-ratio: 300 / 20; margin: 0 auto 3px auto; }
  .slot-repeat-hint  { width: 100%; aspect-ratio: 300 / 26; margin: calc(12px - 3mm) 0 6px 0; }
  .slot-times        { width: 42px; aspect-ratio: 42 / 12; margin-top: 3px; }
  .slot-btn-title    { width: 60px; aspect-ratio: 60 / 15; }

  /* Bottom "LEARN LIVE RECITE..." tagline — was static/missing before,
     now animates EN -> AR -> UR like everything else. The Arabic and
     Urdu artwork (LRMA.png / LRMu.png) render visually larger than the
     English version (LRM-E.png) at the same box height, so they're
     scaled to 0.885 here (0.75 + 18%); English is untouched. The top
     of the page was moved up 9mm and the repeat-hint another 3mm (12mm
     total), so this block's top margin gets +12mm to keep the last two
     lines in exactly the same place as before. */
  .slot-footer-tagline { width: 100%; aspect-ratio: 300 / 34; margin: calc(10px + 16mm) 0 4px 0; }
  .slot-footer-tagline img:nth-child(2),
  .slot-footer-tagline img:nth-child(3) {
    transform: translateX(-50%) scale(calc(0.885 * var(--ar-ur-scale)));
  }

  /* "MEMORIZE WITH PERFECTION" banner — sits at the very top of the card,
     above the Surah field. Same EN -> AR -> UR cycle as everything else. */
  .slot-mwp { width: 100%; aspect-ratio: 300 / 28; margin: 0 0 10px 0; }

  /* Extra -21% on three specific Arabic/Urdu PNGs (on top of the shared
     +15%): PLSA.png + PLSU.png (repeat hint, AR + UR) and mwpu.png (banner,
     UR). 1.15 x 0.79 = ~0.91. */
  :root { --shrink-21: 0.79; }
  .slot-repeat-hint img:nth-child(2),
  .slot-repeat-hint img:nth-child(3),
  .slot-mwp img:nth-child(3) {
    transform: translateX(-50%) scale(calc(var(--ar-ur-scale) * var(--shrink-21)));
  }
</style>
</head>
<body>

<div class="app-container">
<div id="stageMain">
  <div class="fade-slot slot-mwp">
    <img src="/static/mwp.png" alt="Memorize With Perfection (EN)">
    <img src="/static/mwpua.png" alt="Memorize With Perfection (AR)">
    <img src="/static/mwpu.png" alt="Memorize With Perfection (UR)">
  </div>

  <div class="field">
    <div class="fade-slot slot-field-label">
      <img src="/static/sn.png" alt="Surah No. / Name (EN)">
      <img src="/static/sna.png" alt="Surah No. / Name (AR)">
      <img src="/static/snu.png" alt="Surah No. / Name (UR)">
    </div>
    <div class="select-wrapper" onclick="toggleSurahDropdown()">
      <div id="surahSelectedDisplay" class="selected-display">-- Select Surah --</div>
      <img id="surahArabicName" class="surah-arabic-name" alt="" />
      <span id="surahArabicNum" class="surah-arabic-num"></span>
    </div>
    <div id="surahCustomOptions" class="custom-select-options"></div>
  </div>

  <div class="field" id="juzField">
    <div class="fade-slot slot-field-label">
      <img src="/static/juzn.png" alt="Juz No. / Name (EN)">
      <img src="/static/juzna.png" alt="Juz No. / Name (AR)">
      <img src="/static/juznu.png" alt="Juz No. / Name (UR)">
    </div>
    <div class="select-wrapper" onclick="toggleJuzDropdown()">
      <div id="juzSelectedDisplay" class="selected-display">- Select The Juz -</div>
      <select id="juzSelect" onchange="onJuzChange()" style="display:none">
        <option value="">- Select The Juz -</option>
      </select>
      <img id="juzArabicName" class="juz-arabic-name" alt="" />
    </div>
    <div id="juzCustomOptions" class="custom-select-options"></div>
  </div>

  <div class="field">
    <div class="fade-slot slot-field-label">
      <img src="/static/avn.png" alt="Aayah / Verse No. (EN)">
      <img src="/static/avna.png" alt="Aayah / Verse No. (AR)">
      <img src="/static/avnu.png" alt="Aayah / Verse No. (UR)">
    </div>
    <div class="select-wrapper">
      <select id="ayahSelect" onchange="onAyahChange()" disabled>
        <option value="">- Select The Ayah -</option>
      </select>
    </div>
  </div>

  <div class="fade-slot slot-repeat-hint">
    <img src="/static/PLSE.png" alt="Please Set Recitation Repeats (EN)">
    <img src="/static/PLSA.png" alt="Please Set Recitation Repeats (AR)">
    <img src="/static/PLSU.png" alt="Please Set Recitation Repeats (UR)">
  </div>

  <div class="grid3">
    <button type="button" class="btn-big" id="rep21" onclick="setRepeat(21)">
      <img class="big-num" src="/static/21.png" alt="21">
      <div class="fade-slot slot-times">
        <img src="/static/rte.png" alt="TIMES (EN)">
        <img src="/static/rta.png" alt="TIMES (AR)">
        <img src="/static/rtu.png" alt="TIMES (UR)">
      </div>
    </button>
    <button type="button" class="btn-big" id="rep10" onclick="setRepeat(10)">
      <img class="big-num" src="/static/10.png" alt="10">
      <div class="fade-slot slot-times">
        <img src="/static/rte.png" alt="TIMES (EN)">
        <img src="/static/rta.png" alt="TIMES (AR)">
        <img src="/static/rtu.png" alt="TIMES (UR)">
      </div>
    </button>
    <button type="button" class="btn-big" id="rep5" onclick="setRepeat(5)">
      <img class="big-num" src="/static/5.png" alt="5">
      <div class="fade-slot slot-times">
        <img src="/static/rte.png" alt="TIMES (EN)">
        <img src="/static/rta.png" alt="TIMES (AR)">
        <img src="/static/rtu.png" alt="TIMES (UR)">
      </div>
    </button>
  </div>

  <div class="grid3 nav-grid">
    <button type="button" class="btn-small" onclick="prevQari()">
      <div class="fade-slot slot-btn-title">
        <img src="/static/pve.png" alt="PREV (EN)">
        <img src="/static/pva.png" alt="PREV (AR)">
        <img src="/static/pvu.png" alt="PREV (UR)">
      </div>
    </button>
    <button type="button" class="btn-small" onclick="againQari()">
      <div class="fade-slot slot-btn-title">
        <img src="/static/ae.png" alt="AGAIN (EN)">
        <img src="/static/aea.png" alt="AGAIN (AR)">
        <img src="/static/au.png" alt="AGAIN (UR)">
      </div>
    </button>
    <button type="button" class="btn-small" onclick="nextQari()">
      <div class="fade-slot slot-btn-title">
        <img src="/static/ne.png" alt="NEXT (EN)">
        <img src="/static/nea.png" alt="NEXT (AR)">
        <img src="/static/nu.png" alt="NEXT (UR)">
      </div>
    </button>
  </div>

  <div class="status" id="status">Playing 1 of 21: The Qari Abdul Basit Mujawwad</div>
  <div id="players"></div>
</div>

  <div class="fade-slot slot-footer-tagline">
    <img src="/static/LRM-E.png" alt="Learn Live Recite Memorize Teach Share Please Pray (EN)">
    <img src="/static/LRMA.png" alt="Learn Live Recite Memorize Teach Share Please Pray (AR)">
    <img src="/static/LRMu.png" alt="Learn Live Recite Memorize Teach Share Please Pray (UR)">
  </div>
</div>

<script>
  let repeatCount = 21;
  let sequence = [];
  let currentIndex = 0;

  let surahList = [];
  let currentSurah = null;
  let currentAyah = null;
  let currentMaxAyah = 0;

  function setRepeat(n) {
    repeatCount = n;
    if (currentSurah !== null && currentAyah !== null) buildSequence(currentSurah, currentAyah);
  }

  function toggleSurahDropdown() {
    const opts = document.getElementById('surahCustomOptions');
    opts.classList.toggle('show');
  }

  document.addEventListener('click', function(e) {
    const wrapper = document.querySelector('.field');
    if (wrapper && !wrapper.contains(e.target)) {
      document.getElementById('surahCustomOptions').classList.remove('show');
    }
  });

  function updateSurahArabicImage(surah) {
    const img = document.getElementById('surahArabicName');
    if (!img) return;
    const s = surahList.find(x => String(x.number) === String(surah));
    const numEl = document.getElementById('surahArabicNum');
    if (numEl) numEl.textContent = s ? s.number : '';
    if (s && s.image_url) {
      img.src = s.image_url;
      img.style.display = 'block';
    } else {
      img.style.display = 'none';
    }
  }

  function toggleJuzDropdown() {
    document.getElementById('surahCustomOptions').classList.remove('show');
    document.getElementById('juzCustomOptions').classList.toggle('show');
  }

  document.addEventListener('click', function(e) {
    const jf = document.getElementById('juzField');
    if (jf && !jf.contains(e.target)) {
      document.getElementById('juzCustomOptions').classList.remove('show');
    }
  });

  function updateJuzArabicImage() {
    const img = document.getElementById('juzArabicName');
    const sel = document.getElementById('juzSelect');
    if (!img || !sel) return;
    const dispEl = document.getElementById('juzSelectedDisplay');
    if (dispEl) {
      const jj = JUZ_STARTS.find(x => String(x.juz) === String(sel.value));
      dispEl.textContent = jj ? `Juz ${jj.juz} - ${jj.name}` : '- Select The Juz -';
    }
    if (sel.value) {
      img.onerror = () => { img.style.display = 'none'; };
      img.onload = () => { img.style.display = 'block'; };
      img.src = '/juz-name-image?juz=' + encodeURIComponent(sel.value);
    } else {
      img.style.display = 'none';
      img.removeAttribute('src');
    }
  }

  async function loadSurahs() {
    const res = await fetch('/api/surahs');
    const data = await res.json();
    surahList = data.surahs.slice().sort((a, b) => a.number - b.number);
    const container = document.getElementById('surahCustomOptions');
    container.innerHTML = '';
    
    for (const s of surahList) {
      const item = document.createElement('div');
      item.className = 'option-item';
      
      const imgHtml = s.image_url ? `<img class="option-arabic-img" src="${s.image_url}" alt="" />` : '<span></span>';
      
      item.innerHTML = `
        <span class="option-surah-name">${s.number}. ${s.name}</span>
        ${imgHtml}
        <span class="option-surah-num">${s.number}</span>
      `;
      
      item.onclick = (e) => {
        e.stopPropagation();
        selectSurah(s.number);
        container.classList.remove('show');
      };
      
      container.appendChild(item);
    }
  }

  let taawoozUrl = null;
  let bismillahUrl = null;
  let openingPlayed = false;

  async function loadOpening() {
    try {
      const res = await fetch('/api/opening');
      const data = await res.json();
      if (!data.available) return;

      taawoozUrl = data.taawooz_url;
      bismillahUrl = data.bismillah_url;
      armFirstClickOpening();
    } catch (e) {
      console.error('[opening] loadOpening() failed:', e);
    }
  }

  function armFirstClickOpening() {
    document.addEventListener('click', function onFirstClick() {
      document.removeEventListener('click', onFirstClick);
      if (!openingPlayed) playOpeningSequence();
    }, { once: true });
  }

  function playOpeningSequence() {
    if (openingPlayed) return;
    openingPlayed = true;

    const playTrack = (url) => {
      return new Promise((resolve) => {
        if (!url) { resolve(); return; }
        const audio = new Audio(url);
        audio.onended = () => resolve();
        audio.onerror = () => resolve();
        audio.play().catch(() => resolve());
      });
    };

    playTrack(taawoozUrl).then(() => playTrack(bismillahUrl));
  }

  // Every surah except Al-Fatihah (1) and At-Tawbah (9) starts with the
  // Bismillah clip: audio file 002000, 003000 ... 114000 (ayah number 0).
  function ayahStartFor(surah) {
    const s = parseInt(surah, 10);
    return (s === 1 || s === 9) ? 1 : 0;
  }

  // The number shown is the audio serial number itself (001, 002, 003 ...),
  // e.g. file 002001 is "Ayah 1", 114001 is "Ayah 1". Same rule for every
  // surah, including Al-Fatihah and At-Tawbah (which already worked this way).
  function ayahDisplayLabel(surah, a) {
    return a;
  }

  function ayahOptionText(surah, a) {
    if (a === 0) return 'بسم الله الرحمن الرحيم';   // Bismillah (file X000)
    return 'Ayah ' + ayahDisplayLabel(surah, a);
  }

  async function fetchMaxAyah(surah) {
    const res = await fetch('/api/ayah_count?surah=' + surah);
    const data = await res.json();
    return data.max_ayah || 0;
  }

  async function selectSurah(surahVal) {
    const sObj = surahList.find(x => String(x.number) === String(surahVal));
    const display = document.getElementById('surahSelectedDisplay');
    
    if (sObj) {
      display.textContent = `${sObj.number}. ${sObj.name}`;
    } else {
      display.textContent = '-- Select Surah --';
    }
    
    onSurahChange(surahVal);
  }

  async function onSurahChange(surah) {
    updateSurahArabicImage(surah);
    const ayahSel = document.getElementById('ayahSelect');
    ayahSel.innerHTML = '';
    document.getElementById('players').innerHTML = '';
    document.getElementById('status').textContent = 'Playing 1 of 21: The Qari Abdul Basit Mujawwad';
    if (!surah) {
      ayahSel.disabled = true;
      ayahSel.innerHTML = '<option value="">- Select The Ayah -</option>';
      currentSurah = null; currentAyah = null; currentMaxAyah = 0;
      document.getElementById('juzSelect').value = '';
      updateJuzArabicImage();
      return;
    }
    ayahSel.disabled = true;
    ayahSel.innerHTML = '<option value="">Loading...</option>';
    let maxAyah = 0;
    try { maxAyah = await fetchMaxAyah(surah); }
    catch (e) { document.getElementById('status').textContent = 'Could not load ayah list: ' + e; }
    currentSurah = parseInt(surah, 10);
    currentMaxAyah = maxAyah;
    ayahSel.innerHTML = '<option value="">- Select The Ayah -</option>';
    for (let a = ayahStartFor(surah); a <= maxAyah; a++) {
      const opt = document.createElement('option');
      opt.value = a; opt.textContent = ayahOptionText(surah, a);
      ayahSel.appendChild(opt);
    }
    ayahSel.disabled = false;
    document.getElementById('juzSelect').value = '';
    updateJuzArabicImage();
  }

  async function onAyahChange() {
    const surah = currentSurah;
    const ayah = document.getElementById('ayahSelect').value;
    if (!surah || !ayah) {
      document.getElementById('players').innerHTML = '';
      document.getElementById('juzSelect').value = '';
      updateJuzArabicImage();
      return;
    }
    const surahNum = parseInt(surah, 10);
    const ayahNum = parseInt(ayah, 10);
    updateJuzDisplay(surahNum, ayahNum);
    buildSequence(surahNum, ayahNum);
  }

  const JUZ_STARTS = [
    { juz: 1,  surah: 1,  ayah: 1,   name: "Alif Lam Meem" },
    { juz: 2,  surah: 2,  ayah: 142, name: "Sayaqul" },
    { juz: 3,  surah: 2,  ayah: 253, name: "Tilka'r-Rusul" },
    { juz: 4,  surah: 3,  ayah: 93,  name: "Lan Tana Lu" },
    { juz: 5,  surah: 4,  ayah: 24,  name: "Wal-Muhsanat" },
    { juz: 6,  surah: 4,  ayah: 148, name: "La Yuhibbullah" },
    { juz: 7,  surah: 5,  ayah: 82,  name: "Wa Iza Sami'u" },
    { juz: 8,  surah: 6,  ayah: 111, name: "Wa Lau Annana" },
    { juz: 9,  surah: 7,  ayah: 88,  name: "Qalal-Mala" },
    { juz: 10, surah: 8,  ayah: 41,  name: "Wa A'lamu" },
    { juz: 11, surah: 9,  ayah: 93,  name: "Yatazeroon" },
    { juz: 12, surah: 11, ayah: 6,   name: "Wa Mamin Da'abat" },
    { juz: 13, surah: 12, ayah: 53,  name: "Wa Ma Ubrioo" },
    { juz: 14, surah: 15, ayah: 1,   name: "Rubama" },
    { juz: 15, surah: 17, ayah: 1,   name: "Subhanallazi" },
    { juz: 16, surah: 18, ayah: 75,  name: "Qal Alam" },
    { juz: 17, surah: 21, ayah: 1,   name: "Aqtarabo" },
    { juz: 18, surah: 23, ayah: 1,   name: "Qadd Aflaha" },
    { juz: 19, surah: 25, ayah: 21,  name: "Wa Qalallazina" },
    { juz: 20, surah: 27, ayah: 56,  name: "Amman Khalaq" },
    { juz: 21, surah: 29, ayah: 46,  name: "Utlu Ma Oohi" },
    { juz: 22, surah: 33, ayah: 31,  name: "Wa Manyaqnut" },
    { juz: 23, surah: 36, ayah: 28,  name: "Wa Mali" },
    { juz: 24, surah: 39, ayah: 32,  name: "Faman Azlam" },
    { juz: 25, surah: 41, ayah: 47,  name: "Elahe Yuruddo" },
    { juz: 26, surah: 46, ayah: 1,   name: "Ha'a Meem" },
    { juz: 27, surah: 51, ayah: 31,  name: "Qala Fama Khatbukum" },
    { juz: 28, surah: 58, ayah: 1,   name: "Qad Same' Allah" },
    { juz: 29, surah: 67, ayah: 1,   name: "Tabarakallazi" },
    { juz: 30, surah: 78, ayah: 1,   name: "Amma" },
  ];

  function getJuzFor(surah, ayah) {
    if (ayah < 1) ayah = 1;   // the Bismillah clip (ayah 0) belongs with ayah 1
    let result = JUZ_STARTS[0];
    for (const j of JUZ_STARTS) {
      if (surah > j.surah || (surah === j.surah && ayah >= j.ayah)) {
        result = j;
      } else {
        break;
      }
    }
    return result;
  }

  function loadJuzOptions() {
    const juzSel = document.getElementById('juzSelect');
    juzSel.innerHTML = '<option value="">- Select The Juz -</option>';
    for (const j of JUZ_STARTS) {
      const opt = document.createElement('option');
      opt.value = j.juz;
      opt.textContent = `Juz ${j.juz} - ${j.name}`;
      juzSel.appendChild(opt);
    }

    const juzBox = document.getElementById('juzCustomOptions');
    juzBox.innerHTML = '';
    for (const j of JUZ_STARTS) {
      const item = document.createElement('div');
      item.className = 'option-item';
      item.innerHTML = `
        <span class="option-surah-name">Juz ${j.juz} - ${j.name}</span>
        <img class="option-juz-img" src="/juz-name-image?juz=${j.juz}" alt="" onerror="this.style.display='none'" />
      `;
      item.onclick = (e) => {
        e.stopPropagation();
        juzSel.value = String(j.juz);
        juzBox.classList.remove('show');
        onJuzChange();
      };
      juzBox.appendChild(item);
    }
  }

  function updateJuzDisplay(surah, ayah) {
    const j = getJuzFor(surah, ayah);
    document.getElementById('juzSelect').value = String(j.juz);
    updateJuzArabicImage();
  }

  async function onJuzChange() {
    const juzSel = document.getElementById('juzSelect');
    const juzNum = parseInt(juzSel.value, 10);
    updateJuzArabicImage();
    if (!juzNum) {
      document.getElementById('surahSelectedDisplay').textContent = '-- Select Surah --';
      document.getElementById('ayahSelect').value = '';
      document.getElementById('ayahSelect').disabled = true;
      document.getElementById('ayahSelect').innerHTML = '<option value="">- Select The Ayah -</option>';
      document.getElementById('players').innerHTML = '';
      return;
    }
    const j = JUZ_STARTS.find(x => x.juz === juzNum);
    if (!j) return;

    selectSurah(j.surah);
    const maxAyah = await fetchMaxAyah(j.surah);
    currentMaxAyah = maxAyah;

    const minAyah = ayahStartFor(j.surah);
    // a Juz that opens at ayah 1 of a surah starts on that surah's Bismillah
    const targetAyah = (j.ayah <= 1 || j.ayah < minAyah) ? minAyah : j.ayah;

    const ayahSel = document.getElementById('ayahSelect');
    ayahSel.innerHTML = '<option value="">- Select The Ayah -</option>';
    for (let a = minAyah; a <= maxAyah; a++) {
      const opt = document.createElement('option');
      opt.value = a; opt.textContent = ayahOptionText(j.surah, a);
      ayahSel.appendChild(opt);
    }
    ayahSel.value = String(targetAyah);
    ayahSel.disabled = false;

    buildSequence(j.surah, targetAyah);
  }

  async function buildSequence(surah, ayah) {
    currentSurah = surah;
    currentAyah = ayah;
    if (!currentMaxAyah) currentMaxAyah = await fetchMaxAyah(surah);

    const sObj = surahList.find(x => String(x.number) === String(surah));
    if (sObj) {
      document.getElementById('surahSelectedDisplay').textContent = `${sObj.number}. ${sObj.name}`;
    }

    updateSurahArabicImage(surah);
    updateJuzDisplay(surah, ayah);
    document.getElementById('ayahSelect').value = String(ayah);

    document.getElementById('status').textContent = 'Preparing recitations...';
    const res = await fetch(`/api/sequence?surah=${surah}&ayah=${ayah}&times=${repeatCount}`);
    const data = await res.json();
    sequence = data.sequence;
    currentIndex = 0;
    if (sequence.length === 0) {
      document.getElementById('status').textContent = 'No audio found for this Ayah.';
      document.getElementById('players').innerHTML = '';
      return;
    }
    document.getElementById('status').textContent =
      `Playing ${currentIndex + 1} of ${sequence.length}: ${sequence[currentIndex].qari}`;
    renderCurrent();
  }

  function renderCurrent() {
    const container = document.getElementById('players');
    container.innerHTML = '';
    const item = sequence[currentIndex];
    if (!item) return;
    const card = document.createElement('div');
    card.className = 'player-card now-playing';
    card.innerHTML = `<audio id="audioPlayer" controls autoplay src="${item.url}" style="width:100%; height:28px;"></audio>`;
    container.appendChild(card);
    const audioEl = document.getElementById('audioPlayer');
    audioEl.onended = () => { advanceInSequence(); };
    audioEl.onerror = async () => {
      let why = '';
      try { const r = await fetch(item.url, {headers: {Range: 'bytes=0-1'}}); why = ' (server said ' + r.status + ')'; } catch (e) { why = ' (network error)'; }
      document.getElementById('status').textContent = 'Audio failed to load' + why + ' - tap AGAIN';
    };
    document.getElementById('status').textContent =
      `Playing ${currentIndex + 1} of ${sequence.length}: ${item.qari}`;
  }

  function advanceInSequence() {
    if (sequence.length === 0) return;
    if (currentIndex + 1 >= sequence.length) {
      document.getElementById('status').textContent = 'Completed — moving to next Ayah...';
      stepAyah(1);
      return;
    }
    currentIndex += 1;
    renderCurrent();
  }

  function againQari() {
    if (sequence.length === 0) return;
    currentIndex = 0;
    renderCurrent();
  }

  async function stepAyah(direction) {
    if (currentSurah === null || currentAyah === null || surahList.length === 0) return;

    let surah = currentSurah;
    let ayah = currentAyah + direction;
    let maxAyah = currentMaxAyah;
    let minAyah = ayahStartFor(surah);

    if (ayah < minAyah) {
      const idx = surahList.findIndex(s => s.number === surah);
      if (idx <= 0) {
        document.getElementById('status').textContent = 'First Ayah reached.';
        return;
      }
      surah = surahList[idx - 1].number;
      maxAyah = await fetchMaxAyah(surah);
      ayah = maxAyah;
    } else if (ayah > maxAyah) {
      const idx = surahList.findIndex(s => s.number === surah);
      if (idx === -1 || idx >= surahList.length - 1) {
        document.getElementById('status').textContent = 'Last Ayah reached.';
        return;
      }
      surah = surahList[idx + 1].number;
      maxAyah = await fetchMaxAyah(surah);
      ayah = ayahStartFor(surah);
    }

    currentMaxAyah = maxAyah;
    minAyah = ayahStartFor(surah);

    const ayahSel = document.getElementById('ayahSelect');
    ayahSel.innerHTML = '<option value="">- Select The Ayah -</option>';
    for (let a = minAyah; a <= maxAyah; a++) {
      const opt = document.createElement('option');
      opt.value = a; opt.textContent = ayahOptionText(surah, a);
      ayahSel.appendChild(opt);
    }
    ayahSel.value = String(ayah);
    ayahSel.disabled = false;
    updateSurahArabicImage(surah);

    buildSequence(surah, ayah);
  }

  function prevQari() { stepAyah(-1); }
  function nextQari() { stepAyah(1); }

  loadSurahs();
  loadJuzOptions();
  loadOpening();

  // ===== Phone layout engine: lock + fit + anchor to the background art =====
  // Reference phone: 412 x 773 CSS px. Positions below were measured there and
  // stored as fractions of the background image height so they follow the
  // artwork on every screen size.
  const REF_W = 412;              // design width (px sizes were tuned at this width)
  const FOOT_W = 380;             // footer box width inside the design (412 - 2*16)
  const TOP_FRAC = 0.2474;        // banner top, as a fraction of image height
  const FOOT_FRAC = 0.9067;       // centre of the tagline, same fraction
  const FOOT_DOWN = 2 * 3.7795;   // (layout maths for the rows above; do not change)
  const FOOT_EXTRA = 4 * 3.7795;  // extra 4mm push-down for the tagline ONLY (1mm = 3.7795 CSS px)
  const REF_AVAIL = 487.9 + 2 * 3.7795;  // free height between banner top and tagline on the reference phone (includes the 2mm tagline move, so the other rows stay put)
  let bgW = 714, bgH = 1330;      // background_2.jpg size (refined once loaded)

  function fitStage() {
    const cont = document.querySelector('.app-container');
    const main = document.getElementById('stageMain');
    const foot = document.querySelector('.slot-footer-tagline');
    if (!cont || !main || !foot) return;
    const root = document.documentElement;
    if (window.innerWidth > 600) {            // desktop: leave the normal flow layout alone
      main.style.cssText = ''; foot.style.cssText = '';
      root.classList.remove('fit-pending');
      return;
    }
    const W = cont.clientWidth, H = cont.clientHeight;
    if (!W || !H) return;

    main.style.height = ''; main.style.transform = 'none'; foot.style.transform = 'none';
    const natural = main.offsetHeight;        // content height at the 412px design width
    const footH = foot.offsetHeight || (FOOT_W * 34 / 300);

    // background is drawn with "cover", centred
    const sImg = Math.max(W / bgW, H / bgH);
    const Hi = bgH * sImg, offY = (H - Hi) / 2;
    let top = offY + TOP_FRAC * Hi;
    let footCenter = offY + FOOT_FRAC * Hi;
    footCenter += FOOT_DOWN;
    let footY = footCenter + FOOT_EXTRA;      // where the tagline is finally drawn
    if (H < W * 1.15) {                       // landscape / very wide: simple contain fallback
      top = 6; footCenter = H - 6 - footH / 2; footY = footCenter;
    }

    const gap = 6;
    let s = W / REF_W;
    const sMax = (footCenter - top - gap) / (natural + footH / 2);
    s = Math.max(0.3, Math.min(s, sMax));

    // taller phone than the reference -> spread the extra height between rows
    const availDesign = (footCenter - footH * s / 2 - top) / s;
    const extra = Math.max(0, Math.min(availDesign - REF_AVAIL, natural * 0.25));
    if (extra > 0) main.style.height = (natural + extra) + 'px';

    main.style.transform = 'translate(' + ((W - REF_W * s) / 2) + 'px,' + top + 'px) scale(' + s + ')';
    foot.style.transform = 'translate(' + ((W - FOOT_W * s) / 2) + 'px,' + (footY - footH * s / 2) + 'px) scale(' + s + ')';
    root.classList.remove('fit-pending');
  }

  let fitQueued = false;
  function queueFit() {
    if (fitQueued) return;
    fitQueued = true;
    requestAnimationFrame(() => { fitQueued = false; fitStage(); });
  }
  window.addEventListener('resize', queueFit);
  window.addEventListener('orientationchange', () => setTimeout(queueFit, 150));
  if (window.visualViewport) window.visualViewport.addEventListener('resize', queueFit);
  window.addEventListener('load', queueFit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(queueFit);
  ['status', 'players'].forEach(id => {
    const el = document.getElementById(id);
    if (el) new MutationObserver(queueFit).observe(el, { childList: true, characterData: true, subtree: true });
  });
  (function () {
    const im = new Image();
    im.onload = () => { if (im.naturalWidth) { bgW = im.naturalWidth; bgH = im.naturalHeight; queueFit(); } };
    im.src = '/static/background_2.jpg';
  })();
  fitStage();
  setTimeout(() => document.documentElement.classList.remove('fit-pending'), 1500);

  // Lock: no pinch/double-tap zoom or rubber-band scrolling on phones
  // (the surah drop-down list stays scrollable).
  document.addEventListener('gesturestart', e => e.preventDefault());
  document.addEventListener('touchmove', e => {
    if (window.innerWidth <= 600 && !e.target.closest('.custom-select-options')) e.preventDefault();
  }, { passive: false });
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[server]", fmt % args)

    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_audio_bytes(self, data):
        """Serve audio with HTTP Range support (needed by Chrome/Android)."""
        total = len(data)
        rng = self.headers.get("Range")
        start, end, status = 0, total - 1, 200
        if rng and rng.startswith("bytes="):
            try:
                a, _, b = rng[6:].split(",")[0].partition("-")
                if a == "":
                    start = max(0, total - int(b))
                else:
                    start = int(a)
                    if b:
                        end = min(int(b), total - 1)
                if start > end or start >= total:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{total}")
                    self.end_headers()
                    return
                status = 206
            except ValueError:
                start, end, status = 0, total - 1, 200
        chunk = data[start:end + 1]
        self.send_response(status)
        self.send_header("Content-Type", "audio/ogg")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(len(chunk)))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{total}")
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        try:
            self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path in ("/", "/index.html"):
            body = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path.startswith("/static/"):
            filename = path[len("/static/"):]
            file_path = safe_join(STATIC_ROOT, filename)
            if file_path and os.path.isfile(file_path):
                ctype, _ = mimetypes.guess_type(file_path)
                try:
                    with open(file_path, "rb") as f:
                        file_data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", ctype or "image/jpeg")
                    self.send_header("Content-Length", str(len(file_data)))
                    self.end_headers()
                    self.wfile.write(file_data)
                    return
                except OSError:
                    self.send_error(500, "Error reading static file")
                    return
            else:
                self.send_error(404, "Static file not found")
                return

        if path == "/api/debug":
            manifest = load_manifest()
            qaris = manifest.get("qaris", {})
            probe = {}
            for s in (1, 2, 112):
                counts = [len(list_surah_files(q, s)) for q in qaris]
                probe[str(s)] = {"qaris_with_audio": sum(1 for c in counts if c),
                                 "max_ayah": max(counts) if counts else 0}
            idx = _CHAPTER_INDEX if _CHAPTER_INDEX is not None else _build_chapter_index()
            drive_test = {}
            try:
                _fid = manifest.get("bismillah_file_id") or next(iter(next(iter(next(iter(qaris.values())).values())).values()))
                _d = fetch_drive_file_bytes(_fid)
                drive_test = {"ok": True, "bytes": len(_d)}
            except Exception as _e:
                drive_test = {"ok": False, "error": str(_e)[:400]}
            self.send_json({
                "server_version": "diag-3",
                "drive_download_test": drive_test,
                "base_dir": BASE_DIR,
                "chapter_names_dir_exists": os.path.isdir(CHAPTER_NAMES_ROOT),
                "chapter_pngs_found": len(idx),
                "chapter_numbers_missing": [i for i in range(1, 115) if i not in idx],
                "static_dir_exists": os.path.isdir(STATIC_ROOT),
                "manifest_qaris": len(qaris),
                "manifest_surahs_present": len({s for q in qaris.values() for s in q}),
                "audio_probe": probe,
                "service_account_file": SERVICE_ACCOUNT_FILE,
                "service_account_exists": os.path.isfile(SERVICE_ACCOUNT_FILE),
            })
            return

        if path == "/api/surahs":
            surahs = []
            for n in sorted(TEST_SURAHS):
                image_path = find_chapter_name_image(n)
                surahs.append({
                    "number": n,
                    "name": TEST_SURAHS[n],
                    "image_url": f"/chapter-name-image?surah={n}" if image_path else None,
                })
            self.send_json({"surahs": surahs, "juz": JUZ_LABEL})
            return

        if path == "/chapter-name-image":
            qs = parse_qs(parsed.query)
            surah = qs.get("surah", [""])[0]
            image_path = find_chapter_name_image(surah)
            if not image_path:
                self.send_error(404, "Chapter PNG not found")
                return
            try:
                with open(image_path, "rb") as f:
                    image_data = f.read()
            except OSError:
                self.send_error(404, "Chapter PNG unreadable")
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Content-Length", str(len(image_data)))
            self.end_headers()
            self.wfile.write(image_data)
            return

        if path == "/juz-name-image":
            qs = parse_qs(parsed.query)
            juz = qs.get("juz", [""])[0]
            image_path = find_juz_name_image(juz)
            if not image_path:
                self.send_error(404, "Juz PNG not found")
                return
            try:
                with open(image_path, "rb") as f:
                    image_data = f.read()
            except OSError:
                self.send_error(404, "Juz PNG unreadable")
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Content-Length", str(len(image_data)))
            self.end_headers()
            self.wfile.write(image_data)
            return

        if path == "/api/opening":
            taawooz_id = find_standalone_audio(TAAWOOZ_FILE_STEM)
            bismillah_id = find_standalone_audio(BISMILLAH_FILE_STEM)
            self.send_json({
                "available": bool(taawooz_id or bismillah_id),
                "taawooz_url": "/taawooz-audio" if taawooz_id else None,
                "bismillah_url": "/bismillah-audio" if bismillah_id else None,
            })
            return

        if path == "/taawooz-audio":
            file_id = find_standalone_audio(TAAWOOZ_FILE_STEM)
            if not file_id:
                self.send_error(404, "Taawooz file not found")
                return
            try:
                audio_data = fetch_drive_file_bytes(file_id)
            except Exception as e:
                self.send_error(502, f"Error fetching audio from Drive: {e}")
                return
            self.send_audio_bytes(audio_data)
            return

        if path == "/bismillah-audio":
            file_id = find_standalone_audio(BISMILLAH_FILE_STEM)
            if not file_id:
                self.send_error(404, "Bismillah file not found")
                return
            try:
                audio_data = fetch_drive_file_bytes(file_id)
            except Exception as e:
                self.send_error(502, f"Error fetching audio from Drive: {e}")
                return
            self.send_audio_bytes(audio_data)
            return

        if path == "/api/ayah_count":
            qs = parse_qs(parsed.query)
            surah = qs.get("surah", [""])[0]
            qaris = list_qari_folders()
            max_ayah = 0
            for q in qaris:
                files = list_surah_files(q, surah)
                if files:
                    max_ayah = max(max_ayah, files[-1]["ayah"])
            self.send_json({"max_ayah": max_ayah})
            return

        if path == "/api/sequence":
            qs = parse_qs(parsed.query)
            surah = qs.get("surah", [""])[0]
            ayah = int(qs.get("ayah", ["1"])[0])
            times = int(qs.get("times", ["21"])[0])

            qaris = list_qari_folders()
            available = []
            for q in qaris:
                if audio_file_id(q, surah, ayah):
                    available.append({
                        "qari": display_qari_name(q),
                        "qari_folder": q,
                    })

            seq = []
            if available:
                for i in range(times):
                    q_item = available[i % len(available)]
                    seq.append({
                        "qari": q_item["qari"],
                        "url": f"/audio?qari={q_item['qari_folder']}&surah={surah}&ayah={ayah}"
                    })

            self.send_json({"sequence": seq})
            return

        if path == "/audio":
            qs = parse_qs(parsed.query)
            qari = qs.get("qari", [""])[0]
            surah = qs.get("surah", [""])[0]
            ayah = qs.get("ayah", [""])[0]

            file_id = audio_file_id(qari, surah, ayah)
            if not file_id:
                self.send_error(404, "Audio file not found")
                return

            try:
                data = fetch_drive_file_bytes(file_id)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_error(502, f"Error fetching audio from Drive: {e}")
                return
            self.send_audio_bytes(data)
            return

        self.send_error(404, "Not Found")


def run():
    # Load the manifest and confirm Drive credentials up front, so a config
    # mistake fails loudly at startup instead of on someone's first tap.
    load_manifest()
    get_drive_service()
    server_address = ("0.0.0.0", PORT)
    httpd = ThreadingHTTPServer(server_address, Handler)
    print(f"Starting server on port {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == "__main__":
    run()