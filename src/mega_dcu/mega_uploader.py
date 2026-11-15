"""
MEGA Cloud Storage File Uploader.

Performs thread-safe, parallel chunked uploads to MEGA with support
for in-place replacement or original file retention (--keep-original).
Accelerated via bulk AES CBC MAC computation and persistent HTTP keep-alive.
"""

import os
import random
import threading
import requests
import asyncio
import types

# Compatibility shim for Python 3.11+ with tenacity < 6.0 (required by mega.py)
if not hasattr(asyncio, 'coroutine'):
    asyncio.coroutine = types.coroutine

from mega.mega import (
    a32_to_str,
    Counter,
    AES,
    get_chunks,
    str_to_a32,
    base64_url_encode,
    encrypt_attr,
    a32_to_base64,
    encrypt_key,
    make_id
)

# Lock to guarantee thread-safe sequence numbers and JSON-RPC dispatch in mega.py
_mega_api_lock = threading.Lock()


def ensure_mega_client_threadsafe(mega_client):
    """
    Wraps mega_client._api_request with a lock to ensure thread safety
    without blocking concurrent data transfers (uploading file chunks).
    """
    if not getattr(mega_client, '_is_threadsafe', False):
        orig_api_request = mega_client._api_request

        def threadsafe_api_request(*args, **kwargs):
            """Thread-safe wrapper for MEGA JSON-RPC API requests."""
            with _mega_api_lock:
                return orig_api_request(*args, **kwargs)

        mega_client._api_request = threadsafe_api_request
        mega_client._is_threadsafe = True


def fast_upload(mega_client, filename, dest=None, dest_filename=None):
    """
    Optimized upload implementation for MEGA:
      1. Uses C-accelerated bulk CBC MAC calculation (replacing the pure Python 16-byte loop).
      2. Reuses an HTTP Session with Keep-Alive connection pooling across chunk uploads.
      3. Generates unique request transaction tags to avoid collision across concurrent worker threads.
    """
    if dest is None:
        if not hasattr(mega_client, 'root_id'):
            mega_client.get_files()
        dest = mega_client.root_id

    file_size = os.path.getsize(filename)
    ul_url = mega_client._api_request({'a': 'u', 's': file_size})['p']

    ul_key = [random.randint(0, 0xFFFFFFFF) for _ in range(6)]
    k_str = a32_to_str(ul_key[:4])
    count = Counter.new(128, initial_value=((ul_key[4] << 32) + ul_key[5]) << 64)
    aes = AES.new(k_str, AES.MODE_CTR, counter=count)

    mac_str = '\0' * 16
    mac_encryptor = AES.new(k_str, AES.MODE_CBC, mac_str.encode("utf8"))
    iv_str = a32_to_str([ul_key[4], ul_key[5], ul_key[4], ul_key[5]])

    completion_file_handle = None
    session = requests.Session()
    try:
        if file_size > 0:
            with open(filename, 'rb') as input_file:
                for chunk_start, chunk_size in get_chunks(file_size):
                    chunk = input_file.read(chunk_size)

                    # Bulk CBC MAC calculation (C-accelerated AES)
                    encryptor = AES.new(k_str, AES.MODE_CBC, iv_str)
                    last_block_start = max(0, ((len(chunk) - 1) // 16) * 16)
                    prefix = chunk[:last_block_start]
                    if prefix:
                        encryptor.encrypt(prefix)
                    last_block = chunk[last_block_start:]
                    if len(last_block) % 16:
                        last_block += b'\0' * (16 - (len(last_block) % 16))
                    mac_str = mac_encryptor.encrypt(encryptor.encrypt(last_block))

                    # Encrypt chunk with AES CTR and upload via HTTP session
                    enc_chunk = aes.encrypt(chunk)
                    resp = session.post(
                        f"{ul_url}/{chunk_start}",
                        data=enc_chunk,
                        timeout=mega_client.timeout
                    )
                    resp.raise_for_status()
                    completion_file_handle = resp.text
        else:
            resp = session.post(f"{ul_url}/0", data=b'', timeout=mega_client.timeout)
            resp.raise_for_status()
            completion_file_handle = resp.text
    finally:
        session.close()

    file_mac = str_to_a32(mac_str)
    meta_mac = (file_mac[0] ^ file_mac[1], file_mac[2] ^ file_mac[3])

    dest_filename = dest_filename or os.path.basename(filename)
    attribs = {'n': dest_filename}
    encrypt_attribs = base64_url_encode(encrypt_attr(attribs, ul_key[:4]))
    key = [
        ul_key[0] ^ ul_key[4], ul_key[1] ^ ul_key[5],
        ul_key[2] ^ meta_mac[0], ul_key[3] ^ meta_mac[1],
        ul_key[4], ul_key[5], meta_mac[0], meta_mac[1]
    ]
    encrypted_key = a32_to_base64(encrypt_key(key, mega_client.master_key))

    # Commit node creation with a unique request tag for this upload transaction
    req_tag = make_id(10)
    data = mega_client._api_request({
        'a': 'p',
        't': dest,
        'i': req_tag,
        'n': [{
            'h': completion_file_handle,
            't': 0,
            'a': encrypt_attribs,
            'k': encrypted_key
        }]
    })
    return data


def upload_file_to_mega(mega_client, parent_folder_id, original_file_id, file_path, file_name, keep_original=False, suffix=" cmp", start_spacing=""):
    """
    Uploads a compressed PDF back to MEGA.
    
    If keep_original is False:
        - Uploads the compressed file using the original filename.
        - Deletes (destroys) the original uncompressed file node upon successful upload,
          thereby replacing the file in the folder while keeping the folder link intact.
          
    If keep_original is True:
        - Keeps both the original and compressed files in MEGA.
        - Uploads the compressed file with a suffix appended (e.g. 'document cmp.pdf').
        
    Returns:
        [True] on success, or [False, error_message] on failure.
    """
    try:
        ensure_mega_client_threadsafe(mega_client)

        if keep_original:
            stem, ext = os.path.splitext(file_name)
            upload_filename = f"{stem}{suffix}{ext}"
        else:
            upload_filename = file_name

        # Perform optimized chunked upload with keep-alive session and vectorized MAC calculation
        fast_upload(mega_client, filename=file_path, dest=parent_folder_id, dest_filename=upload_filename)

        # If replace mode, remove the old uncompressed node
        if not keep_original:
            try:
                mega_client.destroy(original_file_id)
            except Exception as del_err:
                print(f"\n{start_spacing}⚠️ Uploaded '{upload_filename}' but failed to delete original node: {del_err}")

        return [True]

    except Exception as e:
        return [False, e]
