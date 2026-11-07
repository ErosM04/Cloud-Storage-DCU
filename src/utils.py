import shutil
import os
import re
import json
import random
import threading

# A lock to prevent background threads from corrupting terminal output when printing
print_lock = threading.Lock()


def clean_directory(directory):
    """Removes the given directory and its content."""
    print(f"Removing '{directory}' folder...")
    
    if os.path.exists(directory):
        shutil.rmtree(directory)

    print("Folder removed")


def format_duration(duration):
    """Formats a number to ``xxh xxm xxs``.
    If the duration is less than 1 second, it will be formatted to ``xx.xxs``."""
    if duration > 1:
        duration = int(duration)
    else:
        return f"{round(duration, 2)}s"
    if duration < 60:
        return f"{duration}s"
    elif duration < 3600:
        minutes = int(duration // 60)
        seconds = duration % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = duration % 60
        return f"{hours}h {minutes}m {seconds}s"


_ILLEGAL_WIN_CHARS = re.compile(r'[<>:"/\\|?*]')


def sanitize_name(name):
    r"""
    Replaces illegal Windows file/folder characters with an underscore.
    Illegal characters: < > : " / \ | ? *
    """
    return _ILLEGAL_WIN_CHARS.sub('_', name)


def print_compression_result(result_data):
    """Prints information regarding the results of a file compression."""
    try:
        with print_lock:
            if result_data.compression_success:
                print(f"\n{result_data.start_spacing}▶️ ✅🗜️ '{result_data.file_name}' took "
                      f"{format_duration(result_data.compression_duration)} to compress from "
                      f"{result_data.original_size}KB to {result_data.compressed_size}KB ({result_data.get_compression_percentage()}%)")
            else:
                print(f"\n{result_data.start_spacing}▶️ ⚠️🗜️ Background compression task failed "
                      f"for {result_data.file_name}: {result_data.error_message}")
            
    except Exception as e:
        with print_lock:
            print(f"\n{result_data.start_spacing}▶️ 🔴🗜️ Background compression thread crashed: {e}")


def print_upload_result(future):
    """Prints information regarding the results of a file upload."""
    try:
        result_data = future.result()

        with print_lock:
            if result_data.upload_success:
                print(f"\n{result_data.start_spacing}▶️ ✅☁️ '{result_data.file_name}' successfully uploaded!")
            else:
                print(f"\n{result_data.start_spacing}▶️ ⚠️☁️ Background upload task failed for {result_data.file_name}: {result_data.up_err_mes}")
            
    except Exception as e:
        with print_lock:
            print(f"\n{result_data.start_spacing}▶️ 🔴☁️ Background upload thread crashed: {e}")


def delete_folders_at_end(list_futures,
                          download_dir, 
                          compressed_dir, 
                          delete: bool,
                          delete_d: bool,
                          delete_c: bool,
                          upload: bool):
    """Deletes the downloads and compressed folders based on the given parameters."""
    fail_comp = False
    fail_up = False
    for element in list_futures:
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
    """Calculates and displays summary statistics of compressions and uploads."""
    total_time = 0
    successful_compressions = 0
    successful_uploads = 0
    failed_compressions = 0
    failed_uploads = 0
    total_compression = 0
    w_total_compression = 0
    weights_sum = 0

    for element in data_list:
        result_data = element.result()
        if result_data.compression_success:
            successful_compressions += 1
            total_time += result_data.compression_duration
            total_compression += result_data.get_compression_percentage()
            w_total_compression += result_data.get_compression_percentage() * result_data.compressed_size
            weights_sum += result_data.compressed_size

            if upload:
                if getattr(result_data, 'upload_success', False):
                    successful_uploads += 1
                else:
                    failed_uploads += 1
        else:
            failed_compressions += 1

    print("\n\n📊 --- FINAL STATISTICS ---")
    print(f"Total files processed: {len(data_list)}")
    print(f"✅🗜️ Successful compressions: {successful_compressions}")
    print(f"❌🗜️ Failed compressions: {failed_compressions}")
    if upload:
        print(f"✅☁️ Successful uploads: {successful_uploads}")
        print(f"❌☁️ Failed uploads: {failed_uploads}")

    if successful_compressions > 0:
        print(f"\n🕑 Total time compressing: {format_duration(total_time)}")
        print(f"⏱️ Average time per file: {format_duration(total_time / successful_compressions)}")
        print(f"📉 Average compressed size: {(total_compression / successful_compressions):.2f}%")
        if weights_sum > 0:
            print(f"⚖️📉 Normalized weighted average compressed size: {(w_total_compression / weights_sum):.2f}%")
    else:
        print("\n😢 No files were successfully compressed.")
        if random.randint(1, 100) <= 5:
            print("No files compressed, Jeffry is sad 😢")


def read_folders_ids(location, provider='drive'):
    """Reads a JSON file containing all the folder IDs for the selected provider."""
    if not os.path.exists(location) or os.path.getsize(location) == 0:
        print(f"Folder IDs file '{location}' not found or empty.")
        return None
    
    data = None
    with open(location, "r", encoding="utf-8") as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            print(f"The folder IDs file '{location}' exists but does not contain a valid JSON.")
            return None

    if not isinstance(data, dict):
        print(f"The folder IDs file '{location}' must contain a JSON object.")
        return None

    # Check for provider-specific key: e.g. "drive" or "mega"
    provider_key = 'drive' if provider in ['drive', 'gdrive', 'google'] else 'mega'
    if provider_key in data and isinstance(data[provider_key], list):
        return [str(fid) for fid in data[provider_key]]

    # Fallback to general "ids" key
    if "ids" in data and isinstance(data["ids"], list):
        return [str(fid) for fid in data["ids"]]

    print(f"No folder IDs listed for '{provider_key}' in '{location}'")
    return None


def normalize_extension_list(extensions):
    """
    Takes a string, list of strings, or collection of file extensions,
    and returns a clean set of normalized extensions (lowercase, without leading dot).
    Handles comma-separated values like 'png,jpg' or '.png'.
    """
    if not extensions:
        return set()

    if isinstance(extensions, str):
        extensions = [extensions]

    cleaned = set()
    for item in extensions:
        if not item:
            continue
        # Split by comma in case user passed "pdf,png"
        parts = str(item).split(',')
        for part in parts:
            trimmed = part.strip().lstrip('.').lower()
            if trimmed:
                cleaned.add(trimmed)
    return cleaned


def load_configured_extensions(config_filename="extension.json"):
    """
    Attempts to read extension list from a JSON file.
    Checks config_filename, and also looks in project root.
    Supports either:
      - A JSON array: ["pdf", "png", "jpg"]
      - A JSON object: {"extensions": ["pdf", "png", "jpg"]}
    Returns a set of normalized extensions or None if file doesn't exist or is invalid.
    """
    candidates = [
        config_filename,
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config_filename),
        "extensions.json",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "extensions.json")
    ]

    found_path = None
    for cand in candidates:
        if os.path.exists(cand) and os.path.getsize(cand) > 0:
            found_path = cand
            break

    if not found_path:
        return None

    try:
        with open(found_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return normalize_extension_list(data)
        elif isinstance(data, dict):
            for key in ["extensions", "extension", "exts", "ext"]:
                if key in data and isinstance(data[key], list):
                    return normalize_extension_list(data[key])
        print(f"⚠️ Warning: '{found_path}' does not contain an extension list or valid 'extensions' key.")
        return None
    except Exception as e:
        print(f"⚠️ Warning: Error reading '{found_path}': {e}")
        return None


def resolve_target_extensions(cli_extensions=None, config_filename="extension.json"):
    """
    Resolves the active target extensions:
    1. If specified via CLI (cli_extensions), uses those.
    2. Otherwise, falls back to config_filename (default: 'extension.json').
    3. If neither is available, defaults to all supported extensions.
    """
    from compression_logic.route_compression import get_all_supported_extensions

    if cli_extensions:
        normalized_cli = normalize_extension_list(cli_extensions)
        if normalized_cli:
            print(f"🎯 Target extensions specified via CLI: {', '.join(sorted(normalized_cli))}\n")
            return normalized_cli

    # Fallback to extension.json
    configured = load_configured_extensions(config_filename)
    if configured:
        print(f"📄 Target extensions loaded from '{config_filename}': {', '.join(sorted(configured))}\n")
        return configured

    # Final fallback: all supported
    all_exts = get_all_supported_extensions()
    print(f"ℹ️ No extension specified. Operating on all supported extensions: {', '.join(sorted(all_exts))}\n")
    return all_exts
