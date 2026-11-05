import argparse
import sys

# Configure UTF-8 stdout/stderr on Windows to support emojis cleanly
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


def get_args():
    """Setup and returns the command line argument parser supporting Google Drive and MEGA."""

    # Check for legacy invocation where the user might pass a folder ID without specifying a provider
    if len(sys.argv) > 1 and sys.argv[1] not in ['drive', 'gdrive', 'google', 'mega', '-h', '--help']:
        print(f"⚠️ Error: Missing cloud provider before '{sys.argv[1]}'.")
        print("Please specify 'drive' or 'mega' as the first argument, e.g.:")
        print(f"  py .\\main.py drive {sys.argv[1]}")
        print(f"  py .\\main.py mega {sys.argv[1]}\n")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Download, asynchronously compress and re-upload files (PDFs, images, videos) from Google Drive or MEGA cloud storage.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    subparsers = parser.add_subparsers(
        dest="provider",
        help="Cloud provider to use ('drive' or 'mega')"
    )

    # Common flags shared between both providers
    common_parser = argparse.ArgumentParser(add_help=False)
    setup_common_flags(common_parser)

    # Subparser for Google Drive
    subparsers.add_parser(
        "drive",
        aliases=["gdrive", "google"],
        parents=[common_parser],
        help="Process Google Drive folders",
        description="Download, asynchronously compress and re-upload files from Google Drive."
    )

    # Subparser for MEGA
    mega_parser = subparsers.add_parser(
        "mega",
        parents=[common_parser],
        help="Process MEGA cloud storage folders",
        description="Download, asynchronously compress and re-upload files from MEGA cloud storage."
    )
    setup_mega_flags(mega_parser)

    args = parser.parse_args()

    if args.provider is None:
        parser.print_help()
        sys.exit(1)

    # Normalize provider aliases (e.g. gdrive/google -> drive)
    if args.provider in ['gdrive', 'google']:
        args.provider = 'drive'

    return args


def setup_common_flags(parser: argparse.ArgumentParser):
    """Setup all flags shared across cloud providers."""
    
    # Positional argument for folder ID
    parser.add_argument('folder_id',
                        nargs='?',
                        default=None, 
                        help="The folder ID, handle, or name. If omitted, reads from the default file ('folder_ids.json').")

    # -e / --ext / --extension / --extensions flag
    parser.add_argument('-e', '--ext', '--extension', '--extensions',
                        nargs='+',
                        default=None,
                        help="Specify one or more file extensions to operate on (e.g. -e pdf or -e png jpg mp4).\n"
                             "If omitted, falls back to the list defined in 'extension.json'.")

    # -c / --clean flag
    parser.add_argument('-c', '--clean', 
                        action='store_true',
                        help="Delete the existing downloaded and compressed folders for the selected provider before starting (e.g. 'downloads_drive'/'compressed_drive' or 'downloads_mega'/'compressed_mega').")
    
    # -r / --recursive flag
    parser.add_argument('-r', '--recursive', 
                        action='store_true',
                        help="Recursively search and download files from all subfolders.")
   
    # --rd / --recursive-depth flag
    parser.add_argument('--rd', '--recursive-depth', 
                        type=int,
                        help="Recursively search and download files from all subfolders with given depth.")
    
    # -u / --upload flag
    parser.add_argument('-u', '--upload', 
                        action='store_true',
                        help="Uploads the compressed file back to the cloud storage provider.")
    
    # --pf / --pdfs-first flag
    parser.add_argument('--pf', '--pdfs-first', 
                        action='store_true',
                        help="Before diving into subfolders, process all the PDF files in the current folder.")

    # -n / --number-of-files flag
    parser.add_argument('-n', '--number-of-files',
                        type=int,
                        help="Set the amount of files that can be processed for each given folder. After the limit is reached "
                             "the program stops processing the folder.")
    
    # -d / --delete flag
    parser.add_argument('-d', '--delete', 
                        action='store_true',
                        help="Deletes all downloaded and compressed files after successfully completing the upload. "
                             "This will work only if the upload is enabled (with '-u'). "
                             "If any compression or upload fails no file will be eliminated.")
    
    # -dd / --delete-downloads flag
    parser.add_argument('-dd', '--delete-downloads', 
                        action='store_true',
                        help="Deletes all downloaded files after successfully completing the compression or the upload. "
                             "If any compression or upload fails no file will be eliminated.")
    
    # -dc / --delete-compressed flag
    parser.add_argument('-dc', '--delete-compressed', 
                        action='store_true',
                        help="Deletes all compressed files after successfully completing the upload. "
                             "This will work only if the upload is enabled (with '-u'). "
                             "If any compression or upload fails no file will be eliminated.")
    
    # -t / --thread-count flag
    parser.add_argument('-t', '--thread-count',
                        type=int,
                        default=4,
                        help="Set the amount of cores (each managing a different thread) to use for asynchronous compression and upload. "
                             "The default value is 4 as it is safe for most CPUs (in order not to overload them).")


def setup_mega_flags(parser: argparse.ArgumentParser):
    """Setup flags specific to MEGA cloud storage."""
    parser.add_argument('--keep-original', '--keep-both', '-kb', '-ko',
                        dest='keep_original',
                        action='store_true',
                        default=False,
                        help="When uploading to MEGA, keep both the original uncompressed file and the compressed file "
                             "(the compressed file will be uploaded with suffix added, e.g. 'document cmp.pdf').\n"
                             "By default (without this flag), the original uncompressed file is deleted from MEGA after upload.")

    parser.add_argument('--cmp-suffix',
                        type=str,
                        default=' cmp',
                        help="Custom suffix appended to the compressed file's name when --keep-original is used (default: ' cmp').")
