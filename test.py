"""
==============================================================================
Cloud-Storage-DCU - Automated Test Runner
==============================================================================
Executes in a synchronized sequential manner a series of CLI test commands
using the 'dcu' command for Google Drive and MEGA with varying parameters.

Subfolders inside the provided parent folder are automatically extracted and
sorted in alphabetical order:
  - 1st subfolder -> Test 1
  - 2nd subfolder -> Test 2
  - 3rd subfolder -> Test 3
  - and so on.

HOW TO RUN:
  1. Run both Google Drive and MEGA tests (requires 2 parent folder IDs):
       py test.py <drive_folder_id> <mega_folder_id_or_name>
       (or: py test.py all <drive_folder_id> <mega_folder_id_or_name>)

  2. Run only Google Drive tests (requires 1 parent folder ID):
       py test.py drive <drive_folder_id>

  3. Run only MEGA tests (requires 1 parent folder ID or name):
       py test.py mega <mega_folder_id_or_name>

A summary report table is printed at the end showing the status (PASSED,
FAILED, SKIPPED) and execution duration of each test command.
==============================================================================
"""

import sys
import os
import time
import shutil
import subprocess

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure 'src' directory is in sys.path for direct imports
_src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


# ==============================================================================
# SUBFOLDER EXTRACTION LOGIC
# ==============================================================================

def extract_drive_subfolders(parent_folder_id, service=None):
    """
    Extracts all direct subfolders inside a given Google Drive parent folder,
    sorted in alphabetical order by name.

    Returns:
        List of dicts: [{'id': folder_id, 'name': folder_name}, ...]
    """
    try:
        if not service:
            from drive_dcu.drive_auth import authenticate_gdrive
            from googleapiclient.discovery import build
            creds = authenticate_gdrive()
            service = build('drive', 'v3', credentials=creds)

        print(f"\n🔍 Querying subfolders inside Google Drive parent folder '{parent_folder_id}'...")

        # Fetch parent folder name for display
        try:
            parent_meta = service.files().get(fileId=parent_folder_id, fields="name").execute()
            parent_name = parent_meta.get('name', 'Unknown')
            print(f"📁 Target Drive Parent Folder: '{parent_name}' (ID: {parent_folder_id})")
        except Exception:
            pass

        query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        subfolders = []
        page_token = None

        while True:
            results = service.files().list(
                q=query,
                spaces='drive',
                pageSize=1000,
                fields="nextPageToken, files(id, name)",
                pageToken=page_token
            ).execute()

            for f in results.get('files', []):
                subfolders.append({
                    'id': f['id'],
                    'name': f['name']
                })

            page_token = results.get('nextPageToken')
            if not page_token:
                break

        # Sort subfolders alphabetically by name (case-insensitive)
        subfolders.sort(key=lambda x: x['name'].lower())

        print(f"✅ Found {len(subfolders)} subfolder(s) in Drive parent folder:")
        for idx, sf in enumerate(subfolders, start=1):
            print(f"   [{idx}] {sf['name']} (ID: {sf['id']})")

        return subfolders

    except Exception as e:
        print(f"\n❌ Error extracting Google Drive subfolders: {e}")
        sys.exit(1)


def extract_mega_subfolders(parent_input, mega_client=None):
    """
    Extracts all direct subfolders inside a given MEGA parent folder (by ID, handle, or name),
    sorted in alphabetical order by name.

    Returns:
        List of dicts: [{'id': folder_handle, 'name': folder_name}, ...]
    """
    try:
        if not mega_client:
            from mega_dcu.mega_auth import authenticate_mega
            mega_client = authenticate_mega()

        from mega_dcu.mega_resolver import (
            resolve_mega_folder,
            build_children_index,
            get_node_name,
            is_node_trashed
        )

        print("⏳ Fetching MEGA cloud file structure...")
        all_nodes = mega_client.get_files()

        parent_handle, parent_name = resolve_mega_folder(mega_client, parent_input, all_nodes)
        print(f"\n📁 Target MEGA Parent Folder: '{parent_name}' (Handle: {parent_handle})")
        print("🔍 Querying direct subfolders inside MEGA parent folder...")

        children_index = build_children_index(all_nodes)
        direct_children = children_index.get(parent_handle, [])
        trash_id = getattr(mega_client, 'trashbin_id', None)

        subfolders = []
        for node in direct_children:
            if isinstance(node, dict) and node.get('t') == 1:  # Folder node
                handle = node.get('h')
                if is_node_trashed(handle, all_nodes, trash_id):
                    continue
                name = get_node_name(node, default='Unknown Folder')
                subfolders.append({
                    'id': handle,
                    'name': name
                })

        # Sort subfolders alphabetically by name (case-insensitive)
        subfolders.sort(key=lambda x: x['name'].lower())

        print(f"✅ Found {len(subfolders)} subfolder(s) in MEGA parent folder:")
        for idx, sf in enumerate(subfolders, start=1):
            print(f"   [{idx}] {sf['name']} (Handle: {sf['id']})")

        return subfolders

    except Exception as e:
        print(f"\n❌ Error extracting MEGA subfolders: {e}")
        sys.exit(1)


# ==============================================================================
# TEST DEFINITIONS
# ==============================================================================

def get_drive_tests(subfolders=None):
    """
    Builds the list of test definitions for Google Drive mapped to extracted subfolders.
    The 1st subfolder is mapped to Test 1, 2nd to Test 2, etc.
    """
    if subfolders is None:
        subfolders = []

    def sf_id(idx):
        return subfolders[idx]['id'] if idx < len(subfolders) else ""

    def sf_name(idx):
        return subfolders[idx]['name'] if idx < len(subfolders) else ""

    return [
        {
            "id": 1,
            "provider": "drive",
            "name": "Basic single-folder compression",
            "folder": sf_id(0),
            "folder_name": sf_name(0),
            "args": ["-c"],
        },
        {
            "id": 2,
            "provider": "drive",
            "name": "Extension filtering (-e pdf png)",
            "folder": sf_id(1),
            "folder_name": sf_name(1),
            "args": ["-e", "pdf", "png", "-c"],
        },
        {
            "id": 3,
            "provider": "drive",
            "name": "Recursive depth limit (-r --rd 2)",
            "folder": sf_id(2),
            "folder_name": sf_name(2),
            "args": ["-r", "--rd", "2", "-c"],
        },
        {
            "id": 4,
            "provider": "drive",
            "name": "Files-first traversal (-r --pf)",
            "folder": sf_id(3),
            "folder_name": sf_name(3),
            "args": ["-r", "--pf", "-c"],
        },
        {
            "id": 5,
            "provider": "drive",
            "name": "File limit & thread count (-t 2 -n 5)",
            "folder": sf_id(4),
            "folder_name": sf_name(4),
            "args": ["-t", "2", "-n", "5", "-c"],
        },
        {
            "id": 6,
            "provider": "drive",
            "name": "Compression with re-upload (-u)",
            "folder": sf_id(5),
            "folder_name": sf_name(5),
            "args": ["-u", "-c"],
        },
        {
            "id": 7,
            "provider": "drive",
            "name": "Full pipeline with local cleanup (-u -d)",
            "folder": sf_id(6),
            "folder_name": sf_name(6),
            "args": ["-u", "-d", "-c"],
        },
    ]


def get_mega_tests(subfolders=None):
    """
    Builds the list of test definitions for MEGA mapped to extracted subfolders.
    The 1st subfolder is mapped to Test 1, 2nd to Test 2, etc.
    """
    if subfolders is None:
        subfolders = []

    def sf_id(idx):
        return subfolders[idx]['id'] if idx < len(subfolders) else ""

    def sf_name(idx):
        return subfolders[idx]['name'] if idx < len(subfolders) else ""

    return [
        {
            "id": 1,
            "provider": "mega",
            "name": "Basic single-folder compression",
            "folder": sf_id(0),
            "folder_name": sf_name(0),
            "args": ["-c"],
        },
        {
            "id": 2,
            "provider": "mega",
            "name": "Extension filtering (-e pdf png)",
            "folder": sf_id(1),
            "folder_name": sf_name(1),
            "args": ["-e", "pdf", "png", "-c"],
        },
        {
            "id": 3,
            "provider": "mega",
            "name": "Recursive depth limit (-r --rd 2)",
            "folder": sf_id(2),
            "folder_name": sf_name(2),
            "args": ["-r", "--rd", "2", "-c"],
        },
        {
            "id": 4,
            "provider": "mega",
            "name": "Files-first traversal (-r --pf)",
            "folder": sf_id(3),
            "folder_name": sf_name(3),
            "args": ["-r", "--pf", "-c"],
        },
        {
            "id": 5,
            "provider": "mega",
            "name": "File limit & thread count (-t 2 -n 5)",
            "folder": sf_id(4),
            "folder_name": sf_name(4),
            "args": ["-t", "2", "-n", "5", "-c"],
        },
        {
            "id": 6,
            "provider": "mega",
            "name": "Compression & re-upload replace mode (-u)",
            "folder": sf_id(5),
            "folder_name": sf_name(5),
            "args": ["-u", "-c"],
        },
        {
            "id": 7,
            "provider": "mega",
            "name": "Upload keep-original (-u -kb --cmp-suffix ' cmp')",
            "folder": sf_id(6),
            "folder_name": sf_name(6),
            "args": ["-u", "-kb", "--cmp-suffix", " cmp", "-c"],
        },
    ]


# ==============================================================================
# TEST EXECUTION LOGIC
# ==============================================================================

def format_duration(seconds):
    """Formats seconds into readable string."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    rem_sec = seconds % 60
    return f"{minutes}m {rem_sec:.1f}s"


def run_test(test, dcu_cmd=None):
    """Runs a single test synchronously and records the outcome."""
    folder = (test.get("folder") or "").strip()
    folder_name = test.get("folder_name", "")
    test_id = test["id"]
    provider = test["provider"].upper()
    name = test["name"]

    print(f"\n{'=' * 75}")
    print(f"▶️ RUNNING TEST {test_id} [{provider}]: {name}")
    if folder_name:
        print(f"📁 Target Subfolder: {folder_name} (ID: {folder})")
    elif folder:
        print(f"📁 Target Folder ID: {folder}")
    print(f"{'=' * 75}")

    # Check if a subfolder was available
    if not folder:
        print(f"⚠️ SKIPPED: No subfolder available for Test {test_id} (parent folder contains fewer subfolders than tests).")
        return {
            "test": test,
            "status": "SKIPPED",
            "duration": 0.0,
            "returncode": None,
            "command": "N/A"
        }

    # Construct execution command using the custom dcu command or fallback
    if dcu_cmd:
        base_cmd = [dcu_cmd]
    elif shutil.which("dcu"):
        base_cmd = ["dcu"]
    else:
        base_cmd = [sys.executable, os.path.join(_src_dir, "main.py")]

    cmd = base_cmd + [test["provider"], folder] + test["args"]
    cmd_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in cmd)
    print(f"💻 Command: {cmd_str}\n")

    start_time = time.time()
    try:
        # Run subprocess synchronously, inheriting stdout/stderr for live streaming
        result = subprocess.run(cmd)
        duration = time.time() - start_time
        status = "PASSED" if result.returncode == 0 else "FAILED"

        print(f"\n{'-' * 75}")
        if status == "PASSED":
            print(f"✅ TEST {test_id} [{provider}] FINISHED: {status} in {format_duration(duration)}")
        else:
            print(f"❌ TEST {test_id} [{provider}] FINISHED: {status} (Exit Code: {result.returncode}) in {format_duration(duration)}")
        print(f"{'-' * 75}\n")

        return {
            "test": test,
            "status": status,
            "duration": duration,
            "returncode": result.returncode,
            "command": cmd_str
        }

    except KeyboardInterrupt:
        print("\n\n⚠️ Execution interrupted by user (Ctrl+C).")
        raise
    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ Execution error: {e}")
        return {
            "test": test,
            "status": "ERROR",
            "duration": duration,
            "returncode": -1,
            "command": cmd_str
        }


def print_summary(results):
    """Prints a structured summary of all test executions."""
    print(f"\n\n{'=' * 80}")
    print("📋 TEST EXECUTION SUMMARY REPORT")
    print(f"{'=' * 80}")

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASSED")
    failed = sum(1 for r in results if r["status"] in ["FAILED", "ERROR"])
    skipped = sum(1 for r in results if r["status"] == "SKIPPED")
    total_time = sum(r["duration"] for r in results)

    print(f"{'#':<4} {'Provider':<10} {'Scenario':<42} {'Status':<10} {'Duration':<10}")
    print(f"{'-' * 80}")

    for r in results:
        t = r["test"]
        status_icon = "✅" if r["status"] == "PASSED" else ("❌" if r["status"] in ["FAILED", "ERROR"] else "⚠️")
        status_text = f"{status_icon} {r['status']}"
        dur_text = format_duration(r["duration"]) if r["duration"] > 0 else "-"
        print(f"{t['id']:<4} {t['provider'].upper():<10} {t['name'][:40]:<42} {status_text:<10} {dur_text:<10}")

    print(f"{'-' * 80}")
    print(f"Totals: {total} tests | {passed} passed | {failed} failed | {skipped} skipped")
    print(f"Total time elapsed: {format_duration(total_time)}")
    print(f"{'=' * 80}\n")


def print_usage():
    """Prints CLI usage help."""
    print("\n" + "=" * 75)
    print("🚀 Cloud-Storage-DCU Automated Test Runner")
    print("=" * 75)
    print("Usage:")
    print("  1. Run both Google Drive and MEGA tests (requires 2 IDs):")
    print("       py test.py <drive_folder_id> <mega_folder_id_or_name>")
    print("       py test.py all <drive_folder_id> <mega_folder_id_or_name>")
    print()
    print("  2. Run only Google Drive tests (requires 1 ID):")
    print("       py test.py drive <drive_folder_id>")
    print()
    print("  3. Run only MEGA tests (requires 1 ID):")
    print("       py test.py mega <mega_folder_id_or_name>")
    print("=" * 75 + "\n")


def parse_cli_args(argv):
    """
    Parses CLI arguments.
    Returns:
        tuple (mode, drive_id, mega_id)
        mode in ('drive', 'mega', 'all')
    """
    args = argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print_usage()
        sys.exit(0 if args else 1)

    # Named flags support: --drive <id> and/or --mega <id>
    drive_id = None
    mega_id = None
    if "--drive" in args or "-d" in args or "--mega" in args or "-m" in args:
        i = 0
        while i < len(args):
            if args[i] in ("--drive", "-d") and i + 1 < len(args):
                drive_id = args[i + 1]
                i += 2
            elif args[i] in ("--mega", "-m") and i + 1 < len(args):
                mega_id = args[i + 1]
                i += 2
            else:
                i += 1
        if drive_id and mega_id:
            return 'all', drive_id, mega_id
        if drive_id:
            return 'drive', drive_id, None
        if mega_id:
            return 'mega', None, mega_id

    first_arg = args[0].lower()

    # Subcommand: drive
    if first_arg in ("drive", "google", "gdrive"):
        if len(args) < 2:
            print("❌ Error: Missing Google Drive parent folder ID.")
            print("Usage: py test.py drive <drive_folder_id>")
            sys.exit(1)
        return 'drive', args[1], None

    # Subcommand: mega
    if first_arg == "mega":
        if len(args) < 2:
            print("❌ Error: Missing MEGA parent folder ID/name.")
            print("Usage: py test.py mega <mega_folder_id_or_name>")
            sys.exit(1)
        return 'mega', None, args[1]

    # Subcommand: all
    if first_arg == "all":
        if len(args) < 3:
            print("❌ Error: Running both providers ('all') requires 2 folder IDs: <drive_id> <mega_id>.")
            print("Usage: py test.py all <drive_folder_id> <mega_folder_id_or_name>")
            sys.exit(1)
        return 'all', args[1], args[2]

    # Two positional arguments: py test.py <drive_id> <mega_id>
    if len(args) == 2:
        return 'all', args[0], args[1]

    # Single positional argument without provider
    if len(args) == 1:
        single = args[0]
        print("❌ Error: Running tests for both providers requires 2 folder IDs (Drive and MEGA).")
        print(f"Received only 1 argument: '{single}'.\n")
        print("If you intended to run only one provider, specify it explicitly:")
        print(f"  py test.py drive {single}")
        print(f"  py test.py mega {single}\n")
        print("To run both providers, provide both IDs:")
        print(f"  py test.py {single} <mega_folder_id_or_name>")
        sys.exit(1)

    print_usage()
    sys.exit(1)


def main():
    """Main entrypoint for test runner."""
    dcu_cmd = shutil.which("dcu") or "dcu"

    mode, drive_parent, mega_parent = parse_cli_args(sys.argv)

    print("\n" + "=" * 75)
    print("🚀 Cloud-Storage-DCU Automated Test Runner")
    print(f"CLI Command:   {dcu_cmd}")
    print(f"Execution Mode: {mode.upper()}")
    print("=" * 75)

    tests_to_run = []

    # 1. Google Drive subfolders & tests
    if mode in ('drive', 'all'):
        drive_subfolders = extract_drive_subfolders(drive_parent)
        if not drive_subfolders:
            print(f"⚠️ No subfolders found inside Google Drive folder '{drive_parent}'.")
        tests_to_run.extend(get_drive_tests(drive_subfolders))

    # 2. MEGA subfolders & tests
    if mode in ('mega', 'all'):
        mega_subfolders = extract_mega_subfolders(mega_parent)
        if not mega_subfolders:
            print(f"⚠️ No subfolders found inside MEGA folder '{mega_parent}'.")
        tests_to_run.extend(get_mega_tests(mega_subfolders))

    if not tests_to_run:
        print("❌ No tests configured to run.")
        sys.exit(1)

    print(f"\n📋 Total Tests Queued: {len(tests_to_run)}")

    results = []
    try:
        for test in tests_to_run:
            res = run_test(test, dcu_cmd=dcu_cmd)
            results.append(res)
    except KeyboardInterrupt:
        print("\nStopping remaining tests due to keyboard interrupt...")

    if results:
        print_summary(results)


if __name__ == '__main__':
    main()
