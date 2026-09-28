import sys
from google.oauth2 import service_account as a
from googleapiclient.discovery import build
c = a.Credentials.from_service_account_file(sys.argv[1], scopes=["https://www.googleapis.com/auth/drive.readonly"])
print(build("drive", "v3", credentials=c, cache_discovery=False).files().list(pageSize=1).execute())
