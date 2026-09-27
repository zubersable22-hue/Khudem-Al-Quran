"""
Run this ONCE on your own PC (not on Render) to build manifest.json — a small
index file mapping qari -> surah -> ayah -> Google Drive file_id.

The live server (server.py) reads this manifest instead of asking Google Drive
"what files exist" on every request, which is what keeps it fast and keeps you
well under Drive API rate limits.

Re-run this any time you add/remove/rename files or Qari folders on Drive.

Usage:
    pip install -r requirements.txt
    python build_manifest.py

Requires:
    - service_account.json in this same folder (the key you downloaded from
      Google Cloud Console — the one whose email you shared the Drive folder
      with as Viewer).
    - ROOT_FOLDER_ID below set to your QuranDownload_Opus32 folder's ID.
"""

import json
import re

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ---------------------------------------------------------------------------
SERVICE_ACCOUNT_FILE = "service_account.json"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# From your link: https://drive.google.com/drive/u/1/folders/1auFuV06S9Cx6wbUNFShdEzxke334L4zM
ROOT_FOLDER_ID = "1auFuV06S9Cx6wbUNFShdEzxke334L4zM"

TAAWOOZ_FILE_STEM = "009000"
BISMILLAH_FILE_STEM = "001001"

# Matches filenames like 001001.opus -> surah 001, ayah 001
AYAH_FILENAME_RE = re.compile(r"^(\d{3})(\d{3})\.\w+$")
FOLDER_MIME = "application/vnd.google-apps.folder"
OUTPUT_PATH = "manifest.json"
# ---------------------------------------------------------------------------


def get_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=DRIVE_SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_children(service, folder_id):
    """Returns every direct child (file or folder) of a Drive folder, paginated."""
    items = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType)",
            pageSize=1000,
            pageToken=page_token,
        ).execute()
        items.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return items


def main():
    service = get_service()
    print(f"Reading root folder {ROOT_FOLDER_ID} ...")
    root_children = list_children(service, ROOT_FOLDER_ID)

    qari_folders = [c for c in root_children if c["mimeType"] == FOLDER_MIME]
    loose_files = [c for c in root_children if c["mimeType"] != FOLDER_MIME]

    taawooz_file_id = None
    bismillah_file_id = None
    for f in loose_files:
        stem = f["name"].rsplit(".", 1)[0]
        if stem == TAAWOOZ_FILE_STEM:
            taawooz_file_id = f["id"]
        elif stem == BISMILLAH_FILE_STEM:
            bismillah_file_id = f["id"]

    manifest = {
        "qaris": {},
        "taawooz_file_id": taawooz_file_id,
        "bismillah_file_id": bismillah_file_id,
    }

    print(f"Found {len(qari_folders)} Qari folders. Indexing each one...")
    for qi, qari_folder in enumerate(sorted(qari_folders, key=lambda c: c["name"]), start=1):
        qari_name = qari_folder["name"]
        print(f"  [{qi}/{len(qari_folders)}] {qari_name}")
        surah_folders = [
            c for c in list_children(service, qari_folder["id"])
            if c["mimeType"] == FOLDER_MIME
        ]

        qari_map = {}
        for surah_folder in surah_folders:
            # Surah folder names are things like "001", "002", ... "114"
            try:
                surah_num = int(surah_folder["name"])
            except ValueError:
                print(f"    ! skipping unexpected folder name: {surah_folder['name']}")
                continue

            ayah_files = list_children(service, surah_folder["id"])
            ayah_map = {}
            for af in ayah_files:
                m = AYAH_FILENAME_RE.match(af["name"])
                if not m:
                    continue
                file_surah, file_ayah = int(m.group(1)), int(m.group(2))
                if file_surah == 9 and file_ayah == 0:
                    # This is the in-folder duplicate of the standalone Taawooz
                    # clip for Surah 9 — skip it, same as the original app did.
                    continue
                # Trust the number encoded in the filename over the folder name.
                ayah_map[str(file_ayah)] = af["id"]

            if ayah_map:
                qari_map[str(surah_num)] = ayah_map

        manifest["qaris"][qari_name] = qari_map

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    total_files = sum(
        len(ayahs) for surahs in manifest["qaris"].values() for ayahs in surahs.values()
    )
    print(f"\nDone. Wrote {OUTPUT_PATH}")
    print(f"  Qaris indexed: {len(manifest['qaris'])}")
    print(f"  Total ayah audio files indexed: {total_files}")
    print(f"  Taawooz found: {bool(taawooz_file_id)}")
    print(f"  Bismillah found: {bool(bismillah_file_id)}")


if __name__ == "__main__":
    main()
