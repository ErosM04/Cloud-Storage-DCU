import os
import json
from concurrent.futures import ThreadPoolExecutor
from googleapiclient.discovery import build
import random

from auth import authenticate_gdrive
from downloader import process_folder
from compressor import compress_pdf_ghostscript
from utils import clean_directory, format_duration
from flags import get_args

FOLDER_IDS_LOCATION = "folder_ids.json"


def main(folder_ids_list, args, download_dir="downloads", compressed_dir="compressed"):
    """Setup the Google Drive service and cycles all the given folders."""
    # Clean the directories if the -c flag is used
    if args.clean is not None and args.clean is True:
        clean_directory(download_dir)
        clean_directory(compressed_dir)
    
    # Setup Google Drive service
    creds = authenticate_gdrive()
    service = build('drive', 'v3', credentials=creds)

    future_list = []
    
    # Set up the Thread Pool
    # max_workers is the number of background threads, 4 is generally safe for most CPUs.
    with ThreadPoolExecutor(max_workers=args.thread_count) as executor:
        params = { # Creates parameters for process_folder()
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
            
            params["folder_id"] = folder_id # Adds folder_id to parameters
            kwargs = {k: v for k, v in params.items() if v is not None} # Dictionary comprehension to remove None parameters

            future_list += process_folder(**kwargs)
        
        # Once all files are downloaded, the 'with' block will automatically freeze the main thread 
        # and wait until the remaining background workers finish their active compressions and uploads.
        print(f"\n\n⏳ All files downloaded. Waiting for background compressions {"and uploads" if args.upload else ""} to finish...")

    print("\n\n🎉 All operations complete!\n")

    if (args.delete or args.delete_downloads or args.delete_compressed):
        delete_folders_at_end(future_list, download_dir, compressed_dir, args.delete, args.delete_downloads, args.delete_compressed, args.upload)

    print_final_statistics(future_list, args.upload)


def delete_folders_at_end(list,
                          download_dir, 
                          compressed_dir, 
                          delete: bool, # If all the folder must be deleted
                          delete_d: bool, # If only the download folder must be deleted
                          delete_c: bool, # If only the compressed folder must be deleted
                          upload: bool, # If the upload is enabled
                          ):
    """Deletes the downloads and compressed folders based on the given parameters"""
    fail_comp = False
    fail_up = False
    for element in list:
        res = element.result()
        if res.compression_success is False:
            fail_comp = True
        if upload and getattr(res, 'upload_success', False) is False:
            fail_up = True
        if (fail_comp and upload is False) or (fail_comp and fail_up):
            break
    
    if delete and upload and not fail_comp and not fail_up:
        clean_directory(download_dir)
        clean_directory(compressed_dir)
    elif delete_d and not fail_comp and (not upload or (upload and not fail_up)):
        clean_directory(download_dir)
    elif delete_c and upload and not fail_comp and not fail_up:
        clean_directory(compressed_dir)


def print_final_statistics(data_list, upload: bool):
    total_time = 0
    successful_compressions = 0
    successful_uploads = 0
    failed_compressions = 0
    failed_uploads = 0
    total_compression = 0
    w_total_compression = 0
    weights_sum = 0

    # Loop through every CompressionData object and get the total infos
    for element in data_list:
        result_data = element.result()
        if result_data.compression_success:
            successful_compressions += 1
            total_time += result_data.compression_duration
            total_compression += result_data.get_compression_percentage()
            w_total_compression += result_data.get_compression_percentage() * result_data.compressed_size # value * weighted
            weights_sum += result_data.compressed_size

            if upload:
                if getattr(result_data, 'upload_success', False): # Get named (dinamically created) attribute of the given class
                    successful_uploads += 1
                else:
                    failed_uploads += 1
        else:
            failed_compressions += 1

    print("\n\n📊 --- FINAL STATISTICS ---")
    print(f"Total PDFs processed: {len(data_list)}")
    print(f"✅🗜️ Successful compressions: {successful_compressions}")
    print(f"❌🗜️ Failed compressions: {failed_compressions}")
    if upload:
        print(f"✅☁️ Successful uploads: {successful_uploads}")
        print(f"❌☁️ Failed uploads: {failed_uploads}")

    if successful_compressions > 0:
        print(f"\n🕑 Total time compressing: {format_duration(total_time)}")
        print(f"⏱️ Average time per PDF: {format_duration(total_time / successful_compressions)}")
        print(f"📉 Average compressed size: {(total_compression / successful_compressions):.2f}%")
        print(f"⚖️📉 Normalized weighted average compressed size: {(w_total_compression / weights_sum):.2f}%")
    else:
        print("\n😢 No files were successfully compressed.")
        if(random.randint(1, 100) <= 5):
            print("No PDF-files, Jeffry is sad 😢")



def read_folders_ids(location):
    """Reads a JSON file containg all the folder IDs"""
    if not os.path.exists(location) and os.path.getsize(location) > 0:
        print(f"Folder IDs file '{location}' not found or empty.")
        return
    
    data = None
    with open(location, "r") as file:
        try:
            data = json.load(file)

        except json.JSONDecodeError:
            print(f"The folder IDs file '{location}' exists but does not contain a valid JSON.")
            return

    if not data or not data["ids"]:
        print(f"No folder IDs listed in '{location}'")
        return
    
    ids = []
    for id in data["ids"]:
        ids.append(id)
            
    return ids


if __name__ == '__main__': # Avoids to run the script when file is imported as module
    args=get_args()
    
    if args.folder_id:
        main([args.folder_id], args=args)
    else:
        print("No ID provided in terminal. Reading from file...\n")
        main(read_folders_ids(FOLDER_IDS_LOCATION), args=args)