"""
==============================================================================
Cloud-Storage-DCU - Automated Test Runner
==============================================================================
Executes in a synchronized sequential manner a series of CLI test commands
using the 'dcu' command for Google Drive and MEGA with varying parameters.

HOW TO RUN:
  1. Insert your test folder IDs/names into the DRIVE_FOLDER_IDS and
     MEGA_FOLDER_IDS lists below. Any slot left empty ("") is safely skipped.

  2. Execute the test runner from your terminal:
     - Run all tests (both Google Drive and MEGA):
         py test.py
         (or: python test.py)

     - Run only Google Drive tests:
         py test.py drive

     - Run only MEGA tests:
         py test.py mega

A summary report table is printed at the end showing the status (PASSED,
FAILED, SKIPPED) and execution duration of each test command.
==============================================================================
"""

import sys
import os
import time
import subprocess

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# CONFIGURATION: TARGET CLOUD FOLDER IDS
# ==============================================================================

# Amount of different Google Drive folder IDs needed: 7
DRIVE_FOLDER_IDS = [
    "",  # Test 1: Basic single-folder download & compression (-c)
    "",  # Test 2: Multi-extension filtering (-e pdf png -c)
    "",  # Test 3: Recursive depth search (-r --rd 2 -c)
    "",  # Test 4: Files-first traversal order (-r --pf -c)
    "",  # Test 5: Limited files & custom threads (-t 2 -n 5 -c)
    "",  # Test 6: Compression and re-upload (-u -c)
    "",  # Test 7: Full pipeline with local cleanup (-u -d -c)
]

# Amount of different MEGA folder IDs / names needed: 7
MEGA_FOLDER_IDS = [
    "",  # Test 1: Basic single-folder download & compression (-c)
    "",  # Test 2: Multi-extension filtering (-e pdf png -c)
    "",  # Test 3: Recursive depth search (-r --rd 2 -c)
    "",  # Test 4: Files-first traversal order (-r --pf -c)
    "",  # Test 5: Limited files & custom threads (-t 2 -n 5 -c)
    "",  # Test 6: Compression and re-upload in replace mode (-u -c)
    "",  # Test 7: Upload keeping original file (-u -kb --cmp-suffix " cmp" -c)
]


# ==============================================================================
# TEST DEFINITIONS
# ==============================================================================

def get_drive_tests():
    """Builds the list of test definitions for Google Drive."""
    return [
        {
            "id": 1,
            "provider": "drive",
            "name": "Basic single-folder compression",
            "folder": DRIVE_FOLDER_IDS[0] if len(DRIVE_FOLDER_IDS) > 0 else "",
            "args": ["-c"],
        },
        {
            "id": 2,
            "provider": "drive",
            "name": "Extension filtering (-e pdf png)",
            "folder": DRIVE_FOLDER_IDS[1] if len(DRIVE_FOLDER_IDS) > 1 else "",
            "args": ["-e", "pdf", "png", "-c"],
        },
        {
            "id": 3,
            "provider": "drive",
            "name": "Recursive depth limit (-r --rd 2)",
            "folder": DRIVE_FOLDER_IDS[2] if len(DRIVE_FOLDER_IDS) > 2 else "",
            "args": ["-r", "--rd", "2", "-c"],
        },
        {
            "id": 4,
            "provider": "drive",
            "name": "Files-first traversal (-r --pf)",
            "folder": DRIVE_FOLDER_IDS[3] if len(DRIVE_FOLDER_IDS) > 3 else "",
            "args": ["-r", "--pf", "-c"],
        },
        {
            "id": 5,
            "provider": "drive",
            "name": "File limit & thread count (-t 2 -n 5)",
            "folder": DRIVE_FOLDER_IDS[4] if len(DRIVE_FOLDER_IDS) > 4 else "",
            "args": ["-t", "2", "-n", "5", "-c"],
        },
        {
            "id": 6,
            "provider": "drive",
            "name": "Compression with re-upload (-u)",
            "folder": DRIVE_FOLDER_IDS[5] if len(DRIVE_FOLDER_IDS) > 5 else "",
            "args": ["-u", "-c"],
        },
        {
            "id": 7,
            "provider": "drive",
            "name": "Full pipeline with local cleanup (-u -d)",
            "folder": DRIVE_FOLDER_IDS[6] if len(DRIVE_FOLDER_IDS) > 6 else "",
            "args": ["-u", "-d", "-c"],
        },
    ]


def get_mega_tests():
    """Builds the list of test definitions for MEGA cloud storage."""
    return [
        {
            "id": 1,
            "provider": "mega",
            "name": "Basic single-folder compression",
            "folder": MEGA_FOLDER_IDS[0] if len(MEGA_FOLDER_IDS) > 0 else "",
            "args": ["-c"],
        },
        {
            "id": 2,
            "provider": "mega",
            "name": "Extension filtering (-e pdf png)",
            "folder": MEGA_FOLDER_IDS[1] if len(MEGA_FOLDER_IDS) > 1 else "",
            "args": ["-e", "pdf", "png", "-c"],
        },
        {
            "id": 3,
            "provider": "mega",
            "name": "Recursive depth limit (-r --rd 2)",
            "folder": MEGA_FOLDER_IDS[2] if len(MEGA_FOLDER_IDS) > 2 else "",
            "args": ["-r", "--rd", "2", "-c"],
        },
        {
            "id": 4,
            "provider": "mega",
            "name": "Files-first traversal (-r --pf)",
            "folder": MEGA_FOLDER_IDS[3] if len(MEGA_FOLDER_IDS) > 3 else "",
            "args": ["-r", "--pf", "-c"],
        },
        {
            "id": 5,
            "provider": "mega",
            "name": "File limit & thread count (-t 2 -n 5)",
            "folder": MEGA_FOLDER_IDS[4] if len(MEGA_FOLDER_IDS) > 4 else "",
            "args": ["-t", "2", "-n", "5", "-c"],
        },
        {
            "id": 6,
            "provider": "mega",
            "name": "Compression & re-upload replace mode (-u)",
            "folder": MEGA_FOLDER_IDS[5] if len(MEGA_FOLDER_IDS) > 5 else "",
            "args": ["-u", "-c"],
        },
        {
            "id": 7,
            "provider": "mega",
            "name": "Upload keep-original (-u -kb --cmp-suffix ' cmp')",
            "folder": MEGA_FOLDER_IDS[6] if len(MEGA_FOLDER_IDS) > 6 else "",
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


def run_test(test, dcu_cmd="dcu"):
    """Runs a single test synchronously and records the outcome."""
    folder = (test.get("folder") or "").strip()
    test_id = test["id"]
    provider = test["provider"].upper()
    name = test["name"]

    print(f"\n{'=' * 75}")
    print(f"▶️ RUNNING TEST {test_id} [{provider}]: {name}")
    print(f"{'=' * 75}")

    # Check if a folder ID was configured
    if not folder:
        print(f"⚠️ SKIPPED: No folder ID provided for Test {test_id} in {provider}_FOLDER_IDS.")
        return {
            "test": test,
            "status": "SKIPPED",
            "duration": 0.0,
            "returncode": None,
            "command": "N/A"
        }

    # Construct execution command using the custom dcu command
    cmd = [dcu_cmd, test["provider"], folder] + test["args"]
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


def main():
    """Main entrypoint for test runner."""
    import shutil

    # Locate dcu executable or default to 'dcu'
    dcu_cmd = shutil.which("dcu") or "dcu"

    # Check CLI filter (e.g. 'py test.py drive' or 'py test.py mega')
    filter_arg = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    tests_to_run = []
    if filter_arg in ["all", "drive", "google", "gdrive"]:
        tests_to_run.extend(get_drive_tests())
    if filter_arg in ["all", "mega"]:
        tests_to_run.extend(get_mega_tests())

    if not tests_to_run:
        print(f"Unknown filter '{filter_arg}'. Use: 'all', 'drive', or 'mega'.")
        sys.exit(1)

    print("\n" + "=" * 75)
    print("🚀 Cloud-Storage-DCU Automated Test Runner")
    print(f"CLI Command:   {dcu_cmd}")
    print(f"Tests queued:  {len(tests_to_run)}")
    print("=" * 75)

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
