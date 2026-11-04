import os
import sys
from concurrent.futures import ThreadPoolExecutor

# Ensure parent directory is in sys.path when executed directly
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from compressor import compress_pdf_ghostscript
from utils import clean_directory, delete_folders_at_end, print_final_statistics

try:
    from mega.mega_auth import authenticate_mega
    from mega.mega_downloader import process_mega_folder, resolve_mega_folder
except ImportError:
    from mega_auth import authenticate_mega
    from mega_downloader import process_mega_folder, resolve_mega_folder


def main_mega(folder_ids_list, args, download_dir="downloads_mega", compressed_dir="compressed_mega"):
    """Setup the MEGA client and cycles all the given folders."""
    if not folder_ids_list:
        print("⚠️ No MEGA folder IDs/names provided to process.")
        return

    # Clean the directories if the -c flag is used
    if args.clean is not None and args.clean is True:
        clean_directory(download_dir)
        clean_directory(compressed_dir)
    
    # Authenticate to MEGA (terminal prompt)
    mega_client = authenticate_mega()

    print("⏳ Fetching MEGA cloud file structure...")
    all_nodes = mega_client.get_files()

    future_list = []
    
    with ThreadPoolExecutor(max_workers=args.thread_count) as executor:
        for folder_input in folder_ids_list:
            try:
                folder_id, folder_name = resolve_mega_folder(mega_client, folder_input, all_nodes)
                print(f"\n\n📁 Target MEGA Folder: {folder_name} (Handle: {folder_id})")
            except Exception as e:
                print(f"\n\n⚠️ Could not resolve MEGA folder '{folder_input}'. Error: {e}")
                continue

            sub_futures = process_mega_folder(
                mega_client=mega_client,
                executor=executor,
                compress_func=compress_pdf_ghostscript,
                folder_id=folder_id,
                current_download_dir=download_dir,
                current_compressed_dir=compressed_dir,
                all_nodes=all_nodes,
                recursive=args.recursive,
                recursive_depth=args.rd,
                pdfs_first=args.pf,
                file_limit=args.number_of_files,
                upload=args.upload,
                keep_original=getattr(args, 'keep_original', False),
                cmp_suffix=getattr(args, 'cmp_suffix', ' cmp')
            )
            future_list += sub_futures

        print(f"\n\n⏳ All files downloaded. Waiting for background compressions {'and uploads' if args.upload else ''} to finish...")

    print("\n\n🎉 All operations complete!\n")

    if args.delete or args.delete_downloads or args.delete_compressed:
        delete_folders_at_end(future_list, download_dir, compressed_dir, args.delete, args.delete_downloads, args.delete_compressed, args.upload)

    print_final_statistics(future_list, args.upload)
