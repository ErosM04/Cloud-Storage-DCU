import os
import json
import requests
import asyncio
import types
from pathlib import Path

# Compatibility shim for Python 3.11+ with tenacity < 6.0 (required by mega.py)
if not hasattr(asyncio, 'coroutine'):
    asyncio.coroutine = types.coroutine

from mega.mega import (
    base64_to_a32,
    a32_to_str,
    Counter,
    AES,
    get_chunks,
    str_to_a32,
    RequestError,
)

from utils import format_duration, sanitize_name, print_compression_result, print_upload_result
from compression_logic.route_compression import is_file_eligible, route_compress

from mega_dcu.mega_uploader import upload_file_to_mega

BASE_SPACING = "   "  # Space increase between subfolders' prints


def get_node_name(node, default=""):
    """
    Safely extracts the node name whether node['a'] is a dictionary,
    a JSON string, a plain string, or if node itself is unexpectedly formatted.
    Never raises an AttributeError.
    """
    if not isinstance(node, dict):
        if isinstance(node, str):
            return node
        return default

    a = node.get('a')
    if isinstance(a, dict):
        val = a.get('n')
        return str(val) if val is not None else default

    if isinstance(a, str):
        trimmed = a.strip()
        if trimmed.startswith('MEGA{"') and trimmed.endswith('}'):
            try:
                parsed = json.loads(trimmed[4:])
                if isinstance(parsed, dict) and 'n' in parsed:
                    return str(parsed['n'])
            except Exception:
                pass
        elif trimmed.startswith('{') and trimmed.endswith('}'):
            try:
                parsed = json.loads(trimmed)
                if isinstance(parsed, dict) and 'n' in parsed:
                    return str(parsed['n'])
            except Exception:
                pass
        return trimmed

    if 'name' in node and isinstance(node['name'], str):
        return node['name']
    if 'n' in node and isinstance(node['n'], str):
        return node['n']

    return default


def get_node_path(handle, all_nodes):
    """
    Reconstructs the full folder path (e.g., 'Cloud Drive / Parent / Child')
    from parent node pointers ('p') in all_nodes.
    """
    parts = []
    current_handle = handle
    visited = set()
    while current_handle and current_handle in all_nodes:
        if current_handle in visited:
            break
        visited.add(current_handle)
        node = all_nodes[current_handle]
        if not isinstance(node, dict):
            break
        name = get_node_name(node, default=current_handle)
        parts.append(name)
        if node.get('t') == 2:  # Root reached
            break
        current_handle = node.get('p')
    return " / ".join(reversed(parts)) if parts else handle


def is_node_trashed(handle, all_nodes, trash_id=None):
    """Checks if a node is located inside the Rubbish/Trash bin."""
    current_handle = handle
    visited = set()
    while current_handle and current_handle in all_nodes:
        if current_handle in visited:
            break
        visited.add(current_handle)
        if trash_id and current_handle == trash_id:
            return True
        node = all_nodes[current_handle]
        if not isinstance(node, dict):
            break
        if node.get('t') == 4:  # Trash bin node type
            return True
        current_handle = node.get('p')
    return False


def resolve_mega_folder(mega_client, folder_input, all_nodes=None):
    """
    Resolves a user-provided folder ID, folder name, or 'root' to a valid MEGA node handle and display name.
    Returns:
        tuple (node_handle, folder_name)
    """
    if all_nodes is None:
        all_nodes = mega_client.get_files()

    if not isinstance(all_nodes, dict):
        raise ValueError(f"Expected all_nodes to be a dictionary, got {type(all_nodes).__name__}")

    # Default / Root folder
    if not folder_input or str(folder_input).strip().lower() in ['root', '/', 'clouddrive', 'cloud drive']:
        root_name = "Cloud Drive (Root)"
        root_id = getattr(mega_client, 'root_id', None)
        if not root_id:
            for handle, node in all_nodes.items():
                if isinstance(node, dict) and node.get('t') == 2:
                    root_id = handle
                    break
        return root_id, root_name

    folder_str = str(folder_input).strip()

    # 1. Match by exact node handle
    if folder_str in all_nodes:
        node = all_nodes[folder_str]
        name = get_node_name(node, default='Unknown Folder')
        return folder_str, name

    # 2. Match by folder name (case-insensitive) across active (non-trashed) folders
    trash_id = getattr(mega_client, 'trashbin_id', None)
    matches = []
    for handle, node in all_nodes.items():
        if isinstance(node, dict) and node.get('t') in (1, 2):  # Folder or root node
            if is_node_trashed(handle, all_nodes, trash_id):
                continue
            name = get_node_name(node, default='')
            if name and name.strip().lower() == folder_str.lower():
                matches.append((handle, name))

    if len(matches) == 1:
        return matches[0][0], matches[0][1]

    if len(matches) > 1:
        details = []
        for handle, name in matches:
            path = get_node_path(handle, all_nodes)
            details.append(f"  • Handle: {handle:<10} | Path: {path}")
        details_str = "\n".join(details)
        raise ValueError(
            f"Multiple MEGA folders found matching '{folder_input}'.\n"
            f"Please specify the exact target folder using its Node Handle instead of its name:\n"
            f"{details_str}"
        )

    # 3. Check for MEGA folder URL pattern
    if 'mega.nz/folder/' in folder_str:
        extracted_id = folder_str.split('mega.nz/folder/')[1].split('#')[0]
        if extracted_id in all_nodes:
            node = all_nodes[extracted_id]
            name = get_node_name(node, default='Shared Folder')
            return extracted_id, name

    raise ValueError(f"Could not find any MEGA folder in your account matching '{folder_input}'.")


def download_mega_pdf(mega_client, file_node, dest_dir, file_name, start_spacing=""):
    """
    Downloads and decrypts a file from MEGA directly to dest_dir/file_name,
    displaying real-time download progress and verifying MAC integrity without Windows file locking bugs.
    """
    file_handle = file_node['h']
    k = file_node['k']
    iv = file_node['iv']
    meta_mac = file_node['meta_mac']

    file_data = mega_client._api_request({'a': 'g', 'g': 1, 'n': file_handle})
    if 'g' not in file_data:
        raise RequestError('File not accessible anymore on MEGA servers')

    file_url = file_data['g']
    file_size = file_data['s']
    file_path = os.path.join(dest_dir, file_name)

    input_stream = requests.get(file_url, stream=True, timeout=mega_client.timeout).raw

    k_str = a32_to_str(k)
    counter = Counter.new(128, initial_value=((iv[0] << 32) + iv[1]) << 64)
    aes = AES.new(k_str, AES.MODE_CTR, counter=counter)

    mac_str = '\0' * 16
    mac_encryptor = AES.new(k_str, AES.MODE_CBC, mac_str.encode("utf8"))
    iv_str = a32_to_str([iv[0], iv[1], iv[0], iv[1]])

    download_progress = 0
    with open(file_path, 'wb') as out_f:
        if file_size > 0:
            for chunk_start, chunk_size in get_chunks(file_size):
                chunk = input_stream.read(chunk_size)
                chunk = aes.decrypt(chunk)
                out_f.write(chunk)
                download_progress += len(chunk)

                encryptor = AES.new(k_str, AES.MODE_CBC, iv_str)
                for i in range(0, len(chunk) - 16, 16):
                    block = chunk[i:i + 16]
                    encryptor.encrypt(block)

                if file_size > 16:
                    i += 16
                else:
                    i = 0

                block = chunk[i:i + 16]
                if len(block) % 16:
                    block += b'\0' * (16 - (len(block) % 16))
                mac_str = mac_encryptor.encrypt(encryptor.encrypt(block))

                percent = int(download_progress / file_size * 100)
                print(f"{start_spacing}  ▶️ Download {percent}%.", end='\r', flush=True)
        else:
            print(f"{start_spacing}  ▶️ Download 100%.", end='\r', flush=True)

    print()
    file_mac = str_to_a32(mac_str)
    if (file_mac[0] ^ file_mac[1], file_mac[2] ^ file_mac[3]) != meta_mac:
        raise ValueError('Mismatched MAC verification on downloaded file')

    return file_path


download_mega_file = download_mega_pdf


def build_children_index(all_nodes):
    """Indexes all MEGA nodes by their parent ID in O(N) time for instant O(1) folder queries."""
    index = {}
    if not isinstance(all_nodes, dict):
        return index
    for node in all_nodes.values():
        if not isinstance(node, dict):
            continue
        parent = node.get('p')
        if parent not in index:
            index[parent] = []
        index[parent].append(node)
    return index


def process_mega_folder(mega_client,
                        executor,
                        compress_func=route_compress,
                        folder_id=None,
                        current_download_dir="downloads_mega",
                        current_compressed_dir="compressed_mega",
                        all_nodes=None,
                        children_by_parent=None,
                        target_extensions=None,
                        recursive=False,
                        recursive_depth=None,
                        pdfs_first=False,
                        file_limit=None,
                        upload=False,
                        keep_original=False,
                        cmp_suffix=" cmp",
                        start_spacing=BASE_SPACING):
    """
    Recursively processes MEGA folders to find and download targeted files,
    compresses them with background threads, and optionally uploads them back.
    """
    os.makedirs(current_download_dir, exist_ok=True)
    os.makedirs(current_compressed_dir, exist_ok=True)

    if all_nodes is None:
        all_nodes = mega_client.get_files()

    if children_by_parent is None:
        children_by_parent = build_children_index(all_nodes)

    futures = []

    # Get all direct children of folder_id in O(1) time
    items = children_by_parent.get(folder_id, [])

    if pdfs_first:
        # Move folders (type 1) after files (type 0)
        items = sorted(items, key=lambda x: 1 if isinstance(x, dict) and x.get('t') == 1 else 0)

    for item in items:
        if not isinstance(item, dict):
            continue
        node_type = item.get('t')
        node_handle = item.get('h')
        raw_name = get_node_name(item, default='')
        item_name = sanitize_name(raw_name)

        # Check on file limit
        if file_limit is not None and file_limit <= 0:
            print(f"\n{start_spacing}⚠️ Processable file limit reached")
            break

        # Folder handling
        if node_type == 1:
            can_dive = False
            next_depth = None
            if recursive:
                can_dive = True
            elif recursive_depth is not None and recursive_depth > 0:
                can_dive = True
                next_depth = recursive_depth - 1

            if can_dive:
                print(f"\n{start_spacing}📂 Opening Subfolder: {item_name}/")
                new_download_dir = os.path.join(current_download_dir, item_name)
                new_compressed_dir = os.path.join(current_compressed_dir, item_name)
                sub_futures = process_mega_folder(
                    mega_client=mega_client,
                    executor=executor,
                    compress_func=compress_func,
                    folder_id=node_handle,
                    current_download_dir=new_download_dir,
                    current_compressed_dir=new_compressed_dir,
                    all_nodes=all_nodes,
                    children_by_parent=children_by_parent,
                    target_extensions=target_extensions,
                    recursive=recursive,
                    recursive_depth=next_depth,
                    pdfs_first=pdfs_first,
                    file_limit=file_limit,
                    upload=upload,
                    keep_original=keep_original,
                    cmp_suffix=cmp_suffix,
                    start_spacing=start_spacing + BASE_SPACING
                )
                futures.extend(sub_futures)
            elif recursive_depth == 0:
                print(f"\n{start_spacing}▶️ Skipped Subfolder (run with higher --rd to include): {item_name}/")
            else:
                print(f"\n{start_spacing}▶️ Skipped Subfolder (run with -r to include): {item_name}/")
            continue

        # File handling based on target extensions
        if node_type == 0 and is_file_eligible(item_name, target_extensions):
            if file_limit is not None:
                file_limit -= 1

            print(f"\n{start_spacing}📄 Downloading: {item_name}")
            try:
                file_path = download_mega_pdf(
                    mega_client=mega_client,
                    file_node=item,
                    dest_dir=current_download_dir,
                    file_name=item_name,
                    start_spacing=start_spacing
                )
            except Exception as dl_err:
                print(f"\n{start_spacing}⚠️ Failed to download '{item_name}': {dl_err}")
                continue

            output_path = os.path.join(current_compressed_dir, item_name)
            print(f"{start_spacing}  ▶️ 🔄🗜️ Pushing '{item_name}' to background compression queue...")

            future = executor.submit(
                background_pipeline_mega,
                mega_client,
                file_path,
                output_path,
                folder_id,
                node_handle,
                compress_func,
                start_spacing,
                upload,
                keep_original,
                cmp_suffix
            )
            if upload:
                future.add_done_callback(print_upload_result)
            futures.append(future)
        elif node_type == 0:
            print(f"{start_spacing}  ▶️ Skipped (extension not targeted): {item_name}")

    return futures


def background_pipeline_mega(mega_client, input_path, output_path, parent_folder_id, original_file_id, compress_func, start_spacing, upload=False, keep_original=False, cmp_suffix=" cmp"):
    """
    Executes compression, and if successful, uploads to MEGA (if upload=True).
    """
    result_data = compress_func(input_path, output_path, start_spacing)
    print_compression_result(result_data)

    if upload:
        if result_data.compression_success:
            print(f"\n{start_spacing}🔄☁️ Starting upload to MEGA: {result_data.file_name}...")
            upload_result = upload_file_to_mega(
                mega_client=mega_client,
                parent_folder_id=parent_folder_id,
                original_file_id=original_file_id,
                file_path=output_path,
                file_name=result_data.file_name,
                keep_original=keep_original,
                suffix=cmp_suffix,
                start_spacing=start_spacing
            )
            result_data.upload_success = upload_result[0]
            if not result_data.upload_success:
                result_data.up_err_mes = upload_result[1]
        else:
            result_data.upload_success = False

    return result_data
