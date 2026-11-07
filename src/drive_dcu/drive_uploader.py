import mimetypes
import threading
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Thread-local storage to cache Google Drive service instances per worker thread
_thread_local = threading.local()


def get_drive_service(creds):
    """Returns a thread-local Google Drive service instance to avoid expensive repeated build() calls."""
    service = getattr(_thread_local, 'service', None)
    if service is None or getattr(_thread_local, 'creds', None) != creds:
        _thread_local.service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        _thread_local.creds = creds
    return _thread_local.service


def replace_file_on_drive(creds, file_id, file_path, file_name, start_spacing):
    """Uploads the compressed file back to Google Drive, overwriting the original file's content, thus preserving the original ID.
    Returns a list containing the boolean result and, if it fails, the error message."""
    
    # Retrieve the thread-local Drive service connection
    service = get_drive_service(creds)
    
    try:    
        # Determine the MIME type dynamically based on the file extension
        guessed_type, _ = mimetypes.guess_type(file_path)
        mime_type = guessed_type or 'application/octet-stream'

        # Prepare the file for upload
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

        # update() forces the new bytes into the existing File ID
        service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()
        
        return [True]
        
    except Exception as e:
        return [False, e]
