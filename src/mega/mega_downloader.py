import os
import requests
from pathlib import Path
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

try:
    from mega.mega_uploader import upload_file_to_mega
except ImportError:
    from mega_uploader import upload_file_to_mega

BASE_SPACING = "   "  # Space increase between subfolders' prints


def resolve_mega_folder(mega_client, folder_input, all_nodes=None):
    """
    Resolves a user-provided folder ID, folder name, or 'root' to a valid MEGA node handle and display name.
    Returns:
        tuple (node_handle, folder_name)
    """
    if all_nodes is None:
        all_nodes = mega_client.get_files()

    # Default / Root folder
    if not folder_input or str(folder_input).strip().lower() in ['root', '/', 'clouddrive', 'cloud drive']:
        root_name = "Cloud Drive (Root)"
        root_id = getattr(mega_client, 'root_id', None)
        if not root_id:
            for handle, node in all_nodes.items():
                if node.get('t') == 2:
                    root_id = handle
                    break
        return root_id, root_name

    folder_str = str(folder_input).strip()

    # 1. Match by exact node handle
    if folder_str in all_nodes:
        node = all_nodes[folder_str]
        name = node.get('a', {}).get('n', 'Unknown Folder')
        return folder_str, name

    # 2. Match by folder name (case-insensitive)
    for handle, node in all_nodes.items():
        if node.get('t') == 1:  # Folder node
            name = node.get('a', {}).get('n', '')
            if name.lower() == folder_str.lower():
                return handle, name

    # 3. Check for MEGA folder URL pattern
    if 'mega.nz/folder/' in folder_str:
        extracted_id = folder_str.split('mega.nz/folder/')[1].split('#')[0]
        if extracted_id in all_nodes:
            node = all_nodes[extracted_id]
            name = node.get('a', {}).get('n', 'Shared Folder')
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


def process_mega_folder(mega_client,
                        executor,
                        compress_func,
                        folder_id,
                        current_download_dir,
                        current_compressed_dir,
                        all_nodes=None,
                        recursive=False,
                        recursive_depth=None,
                        pdfs_first=False,
                        file_limit=None,
                        upload=False,
                        keep_original=False,
                        cmp_suffix=" cmp",
                        start_spacing=BASE_SPACING):
    """
    Recursively processes MEGA folders to find and download PDFs,
    compresses them with background threads, and optionally uploads them back.
    """
    os.makedirs(current_download_dir, exist_ok=True)
    os.makedirs(current_compressed_dir, exist_ok=True)

    if all_nodes is None:
        all_nodes = mega_client.get_files()

    futures = []

    # Get all direct children of folder_id
    items = [node for node in all_nodes.values() if node.get('p') == folder_id]

    if pdfs_first:
        # Move folders (type 1) after files (type 0)
        items = sorted(items, key=lambda x: 1 if x.get('t') == 1 else 0)

    for item in items:
        node_type = item.get('t')
        node_handle = item.get('h')
        raw_name = item.get('a', {}).get('n', '')
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

        # PDF files handling
        if node_type == 0 and item_name.lower().endswith('.pdf'):
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
            print(f"{start_spacing}  ▶️ Skipped compression (not a PDF): {item_name}")

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
