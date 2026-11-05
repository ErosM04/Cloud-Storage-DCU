import os
import sys

# Configure UTF-8 stdout/stderr on Windows to support emojis cleanly
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from flags import get_args
from utils import read_folders_ids, resolve_target_extensions

FOLDER_IDS_LOCATION = "folder_ids.json"


def run():
    """Main program entrypoint: parses arguments and dispatches to the chosen provider."""
    args = get_args()

    # Determine target folder ID(s)
    if args.folder_id:
        folder_ids = [args.folder_id]
    else:
        print(f"No {args.provider.upper()} folder ID provided in terminal. Reading from '{FOLDER_IDS_LOCATION}'...\n")
        folder_ids = read_folders_ids(FOLDER_IDS_LOCATION, provider=args.provider)
        if not folder_ids:
            return

    # Resolve target file extensions (from CLI flags, extension.json, or fallback to all supported)
    target_extensions = resolve_target_extensions(args.ext)

    # Dispatch to the chosen cloud provider with provider-specific folder names
    if args.provider == 'drive':
        try:
            from drive.drive_main import main_drive
        except ImportError as e:
            if getattr(e, 'name', None) in ['googleapiclient', 'google_auth_oauthlib', 'google']:
                print("❌ Error: Missing Google Drive dependencies.")
                print("Please install them for your active Python interpreter using:")
                print("  py -m pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib\n")
            else:
                print(f"❌ Error loading Google Drive module: {e}\n")
                import traceback
                traceback.print_exc()
            return
        main_drive(
            folder_ids,
            args=args,
            target_extensions=target_extensions,
            download_dir="downloads_drive",
            compressed_dir="compressed_drive"
        )

    elif args.provider == 'mega':
        try:
            import asyncio
            import types
            if not hasattr(asyncio, 'coroutine'):
                asyncio.coroutine = types.coroutine
            from mega_dcu.mega_main import main_mega
        except ImportError as e:
            if getattr(e, 'name', None) in ['mega', 'Crypto', 'tenacity']:
                print("❌ Error: Missing MEGA dependencies.")
                print("Please install them for your active Python interpreter using:")
                print("  py -m pip install mega.py pycryptodome tenacity\n")
            else:
                print(f"❌ Error loading MEGA module: {e}\n")
                import traceback
                traceback.print_exc()
            return
        main_mega(
            folder_ids,
            args=args,
            target_extensions=target_extensions,
            download_dir="downloads_mega",
            compressed_dir="compressed_mega"
        )


if __name__ == '__main__':
    run()
