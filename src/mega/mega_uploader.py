import os
import threading

# Thread lock to guarantee thread-safe API calls and sequence numbers across worker threads
mega_upload_lock = threading.Lock()


def upload_file_to_mega(mega_client, parent_folder_id, original_file_id, file_path, file_name, keep_original=False, suffix=" cmp", start_spacing=""):
    """
    Uploads a compressed PDF back to MEGA.
    
    If keep_original is False:
        - Uploads the compressed file using the original filename.
        - Deletes (destroys) the original uncompressed file node upon successful upload,
          thereby replacing the file in the folder while keeping the folder link intact.
          
    If keep_original is True:
        - Keeps both the original and compressed files in MEGA.
        - Uploads the compressed file with a suffix appended (e.g. 'document cmp.pdf').
        
    Returns:
        [True] on success, or [False, error_message] on failure.
    """
    try:
        if keep_original:
            stem, ext = os.path.splitext(file_name)
            upload_filename = f"{stem}{suffix}{ext}"
        else:
            upload_filename = file_name

        with mega_upload_lock:
            # Upload the compressed file into the target parent folder
            mega_client.upload(filename=file_path, dest=parent_folder_id, dest_filename=upload_filename)

            # If replace mode, remove the old uncompressed node
            if not keep_original:
                try:
                    mega_client.destroy(original_file_id)
                except Exception as del_err:
                    print(f"\n{start_spacing}⚠️ Uploaded '{upload_filename}' but failed to delete original node: {del_err}")

        return [True]

    except Exception as e:
        return [False, e]
