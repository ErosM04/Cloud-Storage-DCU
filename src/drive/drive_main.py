import os
import sys
from concurrent.futures import ThreadPoolExecutor

# Ensure parent directory is in sys.path when executed directly
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from compressor import compress_pdf_ghostscript
from utils import clean_directory, delete_folders_at_end, print_final_statistics

from drive.drive_auth import authenticate_gdrive
from drive.drive_downloader import process_folder
from googleapiclient.discovery import build


def main_drive(folder_ids_list, args, download_dir="downloads_drive", compressed_dir="compressed_drive"):
    """Setup the Google Drive service and cycles all the given folders."""
    if not folder_ids_list:
        print("⚠️ No Google Drive folder IDs provided to process.")
        return

    # Clean the directories if the -c flag is used
    if args.clean is not None and args.clean is True:
        clean_directory(download_dir)
        clean_directory(compressed_dir)
    
    # Setup Google Drive service
    creds = authenticate_gdrive()
    service = build('drive', 'v3', credentials=creds)

    future_list = []
    
    with ThreadPoolExecutor(max_workers=args.thread_count) as executor:
        params = {
            "creds": creds,
            "service": service, 
            "executor": executor,
            "compress_func": compress_pdf_ghostscript,
            "current_download_dir": download_dir,
            "current_compressed_dir": compressed_dir,
            "recursive": args.recursive,
            "pdfs_first": args.pf,
            "recursive_depth": args.rd,
            "file_limit": args.number_of_files,
            "upload": args.upload
        }
        
        for folder_id in folder_ids_list:
            try:
                folder_metadata = service.files().get(fileId=folder_id, fields="name").execute()
                root_folder_name = folder_metadata.get('name', 'Unknown Folder')
                print(f"\n\n📁 Target Google Drive Folder: {root_folder_name}")
            except Exception as e:
                print(f"\n\n⚠️ Could not fetch folder name (check if the ID is correct). Error: {e}")
            
            params["folder_id"] = folder_id
            kwargs = {k: v for k, v in params.items() if v is not None}

            future_list += process_folder(**kwargs)
        
        print(f"\n\n⏳ All files downloaded. Waiting for background compressions {'and uploads' if args.upload else ''} to finish...")

    print("\n\n🎉 All operations complete!\n")

    if args.delete or args.delete_downloads or args.delete_compressed:
        delete_folders_at_end(future_list, download_dir, compressed_dir, args.delete, args.delete_downloads, args.delete_compressed, args.upload)

    print_final_statistics(future_list, args.upload)
