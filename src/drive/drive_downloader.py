import os
import io
import re
from googleapiclient.http import MediaIoBaseDownload

from utils import format_duration, sanitize_name, print_compression_result, print_upload_result
from compressor import print_lock

from drive.drive_uploader import replace_file_on_drive

BASE_SPACING = "   "  # Space increase between subfolders' prints


def process_folder(creds,
                   service,
                   executor,
                   compress_func,
                   folder_id,
                   current_download_dir,
                   current_compressed_dir,
                   recursive=False,
                   recursive_depth=0,
                   pdfs_first=False,
                   file_limit=None,
                   upload=False,
                   start_spacing=BASE_SPACING):
    """Recursively processes Drive folders to find and download PDF, then compresses them with background threads 
    and if upload is True, sends them back to Drive."""
    # Ensure the local directories exist to mirror the Google Drive structure
    os.makedirs(current_download_dir, exist_ok=True)
    os.makedirs(current_compressed_dir, exist_ok=True)

    query = f"'{folder_id}' in parents and trashed=false"  # Google Drive query
    page_token = None  # Pagination token

    futures = []  # Tracks all futures in this folder

    # Cycles through the pages (Google sends batch of files in pages)
    while True:
        results = service.files().list(
            q=query, 
            spaces='drive',
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token
        ).execute()
        
        items = results.get('files', [])

        if pdfs_first:
            items = push_folders_to_tail(items)

        for item in items:
            file_id = item['id']
            file_name = sanitize_name(item['name'])
            mime_type = item['mimeType']

            # Check on file limit
            if file_limit is not None and file_limit <= 0:
                print(f"\n{start_spacing}⚠️ Processable file limit reached")
                break

            # Folder handling
            if mime_type == 'application/vnd.google-apps.folder':
                if recursive or (not recursive and recursive_depth > 0):
                    print(f"\n{start_spacing}📂 Opening Subfolder: {file_name}/")
                    new_download_dir = os.path.join(current_download_dir, file_name)
                    new_compressed_dir = os.path.join(current_compressed_dir, file_name)
                    subfolder_futures = process_folder(
                        creds=creds,
                        service=service, 
                        executor=executor,
                        compress_func=compress_func,
                        folder_id=file_id, 
                        current_download_dir=new_download_dir,
                        current_compressed_dir=new_compressed_dir,
                        recursive=recursive,
                        recursive_depth=recursive_depth - 1,
                        pdfs_first=pdfs_first,
                        file_limit=file_limit,
                        upload=upload,
                        start_spacing=start_spacing + BASE_SPACING
                    )
                    futures.extend(subfolder_futures)
                elif not recursive and recursive_depth == 0:
                    print(f"\n{start_spacing}▶️ Skipped Subfolder (run with higher --rd to include): {file_name}/")
                else:
                    print(f"\n{start_spacing}▶️ Skipped Subfolder (run with -r to include): {file_name}/")
                continue
                
            # Skip native Google Workspace files (Docs/Sheets/Slides)
            elif "application/vnd.google-apps" in mime_type:
                continue

            # PDF files handling
            if file_name.lower().endswith('.pdf') or mime_type == 'application/pdf':              
                if file_limit is not None:
                    file_limit -= 1

                print(f"\n{start_spacing}📄 Downloading: {file_name}")
                
                request = service.files().get_media(fileId=file_id)
                file_path = os.path.join(current_download_dir, file_name)
                
                with io.FileIO(file_path, mode='wb') as fh:
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        print(f"{start_spacing}  ▶️ Download {int(status.progress() * 100)}%.", end='\r', flush=True)
                print()
                
                output_path = os.path.join(current_compressed_dir, file_name)
                print(f"{start_spacing}  ▶️ 🔄🗜️ Pushing '{file_name}' to background compression queue...")

                # Submits the function and arguments to the background thread pool
                future = executor.submit(background_pipeline, creds, file_path, output_path, file_id, compress_func, start_spacing, upload)
                if upload:
                    future.add_done_callback(print_upload_result)
                futures.append(future)
            else:
                print(f"{start_spacing}  ▶️ Skipped compression (not a PDF): {file_name}")
                pass

        page_token = results.get('nextPageToken', None)
        if page_token is None:
            break

    return futures


def background_pipeline(creds, input_path, output_path, original_file_id, compress_func, start_spacing, upload=False):
    """Executes the compression, and if successful, executes the upload (if upload is True)."""
    result_data = compress_func(input_path, output_path, start_spacing)
    print_compression_result(result_data)

    if upload:
        if result_data.compression_success:
            print(f"\n{start_spacing}🔄☁️ Starting upload for replacement: {result_data.file_name}...")
            upload_result = replace_file_on_drive(creds, original_file_id, output_path, result_data.file_name, start_spacing)
            result_data.upload_success = upload_result[0]
            if not result_data.upload_success:
                result_data.up_err_mes = upload_result[1]
        else:
            result_data.upload_success = False
        
    return result_data


def push_folders_to_tail(list_items):
    """Takes a list and pushes to the tail all the Google Drive folder elements."""
    index = 0
    virtual_len = len(list_items)

    while index < virtual_len:
        if list_items[index]['mimeType'] == 'application/vnd.google-apps.folder':
            list_items.append(list_items[index])
            list_items.pop(index)
            index -= 1
            virtual_len -= 1
        index += 1
    
    return list_items
