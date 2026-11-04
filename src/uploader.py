from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def replace_file_on_drive(creds, file_id, file_path, file_name, start_spacing):
    """Uploads the compressed file back to Google Drive, overwriting the original file's content, thus preserving the orginal ID.
    Returns a list containg the boolean result and, if it fails, the error message."""
    
    # Create a fresh, thread-safe connection to Google Drive for this specific upload
    service = build('drive', 'v3', credentials=creds)
    
    try:    
        # Prepare the file for upload
        media = MediaFileUpload(file_path, mimetype='application/pdf', resumable=True)

        # update() forces the new bytes into the existing File ID
        service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()
        
        return [True]
        
    except Exception as e:
        return [False, e]