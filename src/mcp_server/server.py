"""
Model Context Protocol (MCP) Server for Cloud-Storage-DCU.

Exposes Google Drive and MEGA cloud compression pipelines, folder inspection,
and local compression engines as typed FastMCP tool calls for AI agents.
Protects the stdio JSON-RPC transport by routing diagnostic output to stderr.
"""

import os
import sys
import contextlib
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Any

# Ensure parent directory is in sys.path
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# FastMCP compatibility shim supporting both MCP 1.x and MCP 2.x
try:
    from mcp.server.fastmcp import FastMCP
except (ImportError, ModuleNotFoundError):
    from mcp.server import MCPServer as FastMCP

from compression_logic.route_compression import (
    route_compress,
    is_file_eligible,
    get_category_for_extension,
    PDF_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
)
from utils import (
    clean_directory,
    sanitize_name,
    normalize_extension_list,
)
from drive_dcu.drive_auth import find_token_file, SCOPES
from drive_dcu.drive_downloader import process_folder
from mega_dcu.mega_auth import load_cached_session
from mega_dcu.mega_resolver import (
    resolve_mega_folder,
    build_children_index,
    get_node_name,
    get_node_path,
    is_node_trashed,
)
from mega_dcu.mega_downloader import process_mega_folder

# Initialize FastMCP Server
mcp = FastMCP("cloud-storage-dcu")


@contextlib.contextmanager
def redirect_stdout_to_stderr():
    """
    Redirects stdout to stderr during tool execution.
    In stdio transport, stdout is reserved strictly for JSON-RPC messages.
    Routing prints/progress to stderr prevents corrupting the agent communication channel.
    """
    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        yield
    finally:
        sys.stdout = old_stdout


# -----------------------------------------------------------------------------
# AUTHENTICATION HELPERS
# -----------------------------------------------------------------------------

def _get_drive_service_silent():
    """Returns an authorized Google Drive service or raises PermissionError (never prompts)."""
    token_path = find_token_file()
    if not token_path or not os.path.exists(token_path):
        raise PermissionError(
            "Google Drive token.json not found. Please log in once via the CLI ('dcu drive <folder_id>') to authorize."
        )

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        raise PermissionError(
            "Google Drive credentials are invalid or expired without a refresh token. Re-run CLI authentication ('dcu drive <folder_id>')."
        )

    return build('drive', 'v3', credentials=creds), creds


def _get_mega_client_silent():
    """Returns an authenticated MEGA client or raises PermissionError (never prompts)."""
    session = load_cached_session()
    if not session:
        raise PermissionError(
            "MEGA active session (.mega_session.json) not found or expired. Please run CLI authentication once ('dcu mega <folder_id>')."
        )
    mega_client, email = session
    return mega_client, email


# -----------------------------------------------------------------------------
# MCP TOOLS
# -----------------------------------------------------------------------------

@mcp.tool()
def check_cloud_auth(provider: str = "all") -> Dict[str, Any]:
    """
    Checks if credentials for Google Drive and/or MEGA are valid and active.
    Provider: 'drive', 'mega', or 'all'.
    Returns authentication status and account details without prompting for input.
    """
    results = {}
    target_providers = ["drive", "mega"] if provider.lower() == "all" else [provider.lower()]

    if "drive" in target_providers:
        try:
            service, _ = _get_drive_service_silent()
            about = service.about().get(fields="user(emailAddress,displayName)").execute()
            user_info = about.get("user", {})
            results["drive"] = {
                "authenticated": True,
                "email": user_info.get("emailAddress", "Unknown"),
                "display_name": user_info.get("displayName", "User")
            }
        except Exception as e:
            results["drive"] = {
                "authenticated": False,
                "error": str(e)
            }

    if "mega" in target_providers:
        try:
            _, email = _get_mega_client_silent()
            results["mega"] = {
                "authenticated": True,
                "account": email or "Active Session"
            }
        except Exception as e:
            results["mega"] = {
                "authenticated": False,
                "error": str(e)
            }

    return results


@mcp.tool()
def get_supported_file_types() -> Dict[str, Any]:
    """
    Returns the file extensions supported by Cloud-Storage-DCU categorized by compression engine:
    PDF (Ghostscript), Image (Pillow), and Video (FFmpeg).
    """
    return {
        "pdf_extensions": sorted(list(PDF_EXTENSIONS)),
        "image_extensions": sorted(list(IMAGE_EXTENSIONS)),
        "video_extensions": sorted(list(VIDEO_EXTENSIONS)),
        "default_target": [".pdf"]
    }


@mcp.tool()
def resolve_cloud_folder(provider: str, folder_input: str) -> Dict[str, Any]:
    """
    Resolves a folder name, folder ID, or 'root' to its unique cloud ID/handle and display name.
    Provider: 'drive' or 'mega'.
    folder_input: Folder ID, node handle, or folder name.
    """
    prov = provider.lower()
    with redirect_stdout_to_stderr():
        if prov in ["drive", "gdrive"]:
            service, _ = _get_drive_service_silent()
            folder_clean = folder_input.strip()

            if folder_clean.lower() in ['root', '/', 'clouddrive', 'cloud drive']:
                return {
                    "provider": "drive",
                    "folder_id": "root",
                    "folder_name": "My Drive (Root)"
                }

            # 1. Try direct ID lookup
            try:
                meta = service.files().get(fileId=folder_clean, fields="id, name, mimeType, trashed").execute()
                if meta.get('mimeType') == 'application/vnd.google-apps.folder' and not meta.get('trashed'):
                    return {
                        "provider": "drive",
                        "folder_id": meta.get('id'),
                        "folder_name": meta.get('name')
                    }
            except Exception:
                pass

            # 2. Try lookup by name
            escaped_name = folder_clean.replace("'", "\\'")
            query = f"mimeType='application/vnd.google-apps.folder' and name='{escaped_name}' and trashed=false"
            res = service.files().list(q=query, spaces='drive', fields="files(id, name)").execute()
            files = res.get('files', [])

            if len(files) == 1:
                return {
                    "provider": "drive",
                    "folder_id": files[0]['id'],
                    "folder_name": files[0]['name']
                }
            elif len(files) > 1:
                matches = [{"id": f['id'], "name": f['name']} for f in files]
                return {
                    "error": f"Multiple Drive folders found matching '{folder_input}'. Use folder ID instead.",
                    "matches": matches
                }
            return {"error": f"Could not find any Google Drive folder matching '{folder_input}'"}

        elif prov == "mega":
            mega_client, _ = _get_mega_client_silent()
            all_nodes = mega_client.get_files()
            handle, name = resolve_mega_folder(mega_client, folder_input, all_nodes)
            path = get_node_path(handle, all_nodes)
            return {
                "provider": "mega",
                "folder_id": handle,
                "folder_name": name,
                "path": path
            }

        return {"error": f"Unsupported provider: '{provider}'. Must be 'drive' or 'mega'."}


@mcp.tool()
def list_cloud_folder_contents(
    provider: str,
    folder_input: str,
    target_extensions: Optional[List[str]] = None,
    recursive: bool = False,
    max_depth: int = 1
) -> Dict[str, Any]:
    """
    Lists the files and subfolders in a target cloud folder.
    Identifies which files are eligible for compression based on target_extensions.
    """
    prov = provider.lower()
    allowed_exts = normalize_extension_list(target_extensions) if target_extensions else None

    with redirect_stdout_to_stderr():
        if prov in ["drive", "gdrive"]:
            service, _ = _get_drive_service_silent()
            res_info = resolve_cloud_folder(provider="drive", folder_input=folder_input)
            if "error" in res_info:
                return res_info
            target_id = res_info["folder_id"]
            folder_name = res_info["folder_name"]

            query = f"'{target_id}' in parents and trashed=false"
            results = service.files().list(
                q=query,
                spaces='drive',
                pageSize=1000,
                fields="files(id, name, mimeType, size)"
            ).execute()

            files_list = []
            subfolders_list = []
            total_size_bytes = 0

            for f in results.get('files', []):
                fname = sanitize_name(f.get('name', ''))
                mime = f.get('mimeType', '')
                if mime == 'application/vnd.google-apps.folder':
                    subfolders_list.append({"id": f['id'], "name": fname, "type": "folder"})
                else:
                    sz = int(f.get('size', 0)) if f.get('size') else 0
                    total_size_bytes += sz
                    files_list.append({
                        "id": f['id'],
                        "name": fname,
                        "type": "file",
                        "size_bytes": sz,
                        "category": get_category_for_extension(fname) or "other",
                        "eligible_for_compression": is_file_eligible(fname, allowed_exts)
                    })

            return {
                "provider": "drive",
                "folder_id": target_id,
                "folder_name": folder_name,
                "total_files": len(files_list),
                "eligible_files": sum(1 for item in files_list if item["eligible_for_compression"]),
                "subfolders_count": len(subfolders_list),
                "total_size_bytes": total_size_bytes,
                "subfolders": subfolders_list,
                "files": files_list
            }

        elif prov == "mega":
            mega_client, _ = _get_mega_client_silent()
            all_nodes = mega_client.get_files()
            handle, name = resolve_mega_folder(mega_client, folder_input, all_nodes)
            children_index = build_children_index(all_nodes)
            trash_id = getattr(mega_client, 'trashbin_id', None)

            direct_children = children_index.get(handle, [])
            files_list = []
            subfolders_list = []
            total_size_bytes = 0

            for node in direct_children:
                if not isinstance(node, dict):
                    continue
                node_handle = node.get('h')
                node_name = sanitize_name(get_node_name(node, default='Unknown'))
                node_type = node.get('t')

                if is_node_trashed(node_handle, all_nodes, trash_id):
                    continue

                if node_type == 1:
                    subfolders_list.append({"id": node_handle, "name": node_name, "type": "folder"})
                elif node_type == 0:
                    sz = node.get('s', 0)
                    total_size_bytes += sz
                    files_list.append({
                        "id": node_handle,
                        "name": node_name,
                        "type": "file",
                        "size_bytes": sz,
                        "category": get_category_for_extension(node_name) or "other",
                        "eligible_for_compression": is_file_eligible(node_name, allowed_exts)
                    })

            return {
                "provider": "mega",
                "folder_id": handle,
                "folder_name": name,
                "total_files": len(files_list),
                "eligible_files": sum(1 for item in files_list if item["eligible_for_compression"]),
                "subfolders_count": len(subfolders_list),
                "total_size_bytes": total_size_bytes,
                "subfolders": subfolders_list,
                "files": files_list
            }

        return {"error": f"Unsupported provider: '{provider}'"}


@mcp.tool()
def compress_cloud_folder(
    provider: str,
    folder_input: str,
    target_extensions: Optional[List[str]] = None,
    recursive: bool = False,
    recursive_depth: Optional[int] = None,
    pdfs_first: bool = False,
    upload: bool = True,
    keep_original: bool = False,
    cmp_suffix: str = " cmp",
    file_limit: Optional[int] = None,
    thread_count: int = 4,
    clean_temp_dirs: bool = True
) -> Dict[str, Any]:
    """
    Executes an end-to-end cloud file compression pipeline:
      1. Downloads eligible files from the target cloud folder.
      2. Compresses them asynchronously in background threads.
      3. Uploads the compressed files back to cloud storage (replacing or with suffix).
      4. Aggregates and returns exact size reductions and space savings.
    """
    prov = provider.lower()
    allowed_exts = normalize_extension_list(target_extensions) if target_extensions else None
    download_dir = os.path.join(os.getcwd(), f"downloads_mcp_{prov}")
    compressed_dir = os.path.join(os.getcwd(), f"compressed_mcp_{prov}")

    clean_directory(download_dir)
    clean_directory(compressed_dir)

    with redirect_stdout_to_stderr():
        try:
            future_list = []
            target_folder_name = "Unknown"

            if prov in ["drive", "gdrive"]:
                service, creds = _get_drive_service_silent()
                res_info = resolve_cloud_folder(provider="drive", folder_input=folder_input)
                if "error" in res_info:
                    return res_info
                folder_id = res_info["folder_id"]
                target_folder_name = res_info["folder_name"]

                with ThreadPoolExecutor(max_workers=thread_count) as executor:
                    future_list = process_folder(
                        creds=creds,
                        service=service,
                        executor=executor,
                        compress_func=route_compress,
                        folder_id=folder_id,
                        current_download_dir=download_dir,
                        current_compressed_dir=compressed_dir,
                        target_extensions=allowed_exts,
                        recursive=recursive,
                        recursive_depth=recursive_depth,
                        pdfs_first=pdfs_first,
                        file_limit=file_limit,
                        upload=upload
                    )

            elif prov == "mega":
                mega_client, _ = _get_mega_client_silent()
                all_nodes = mega_client.get_files()
                folder_id, target_folder_name = resolve_mega_folder(mega_client, folder_input, all_nodes)
                children_by_parent = build_children_index(all_nodes)

                with ThreadPoolExecutor(max_workers=thread_count) as executor:
                    future_list = process_mega_folder(
                        mega_client=mega_client,
                        executor=executor,
                        compress_func=route_compress,
                        folder_id=folder_id,
                        current_download_dir=download_dir,
                        current_compressed_dir=compressed_dir,
                        all_nodes=all_nodes,
                        children_by_parent=children_by_parent,
                        target_extensions=allowed_exts,
                        recursive=recursive,
                        recursive_depth=recursive_depth,
                        pdfs_first=pdfs_first,
                        file_limit=file_limit,
                        upload=upload,
                        keep_original=keep_original,
                        cmp_suffix=cmp_suffix
                    )
            else:
                return {"error": f"Unsupported provider: '{provider}'"}

            # Process collected futures
            file_results = []
            total_orig_kb = 0.0
            total_comp_kb = 0.0
            succeeded = 0
            failed = 0

            for f in future_list:
                try:
                    res = f.result()
                    if res.compression_success:
                        succeeded += 1
                        total_orig_kb += res.original_size
                        total_comp_kb += res.compressed_size
                    else:
                        failed += 1

                    item_stat = {
                        "file_name": res.file_name,
                        "original_size_kb": res.original_size,
                        "compressed_size_kb": res.compressed_size,
                        "saved_space_kb": round(res.original_size - res.compressed_size, 2) if res.compression_success else 0.0,
                        "percentage": res.get_compression_percentage(),
                        "compression_success": res.compression_success,
                        "upload_success": getattr(res, 'upload_success', None),
                        "error_message": res.error_message
                    }
                    file_results.append(item_stat)
                except Exception as ex:
                    failed += 1
                    file_results.append({"error": str(ex), "compression_success": False})

            total_saved_kb = round(total_orig_kb - total_comp_kb, 2)
            overall_pct = round((100 * total_comp_kb) / total_orig_kb, 2) if total_orig_kb > 0 else 0.0

            return {
                "status": "success" if succeeded > 0 or len(future_list) == 0 else "failed",
                "provider": prov,
                "folder_name": target_folder_name,
                "folder_id": folder_input,
                "total_files_processed": len(file_results),
                "succeeded": succeeded,
                "failed": failed,
                "total_original_kb": round(total_orig_kb, 2),
                "total_compressed_kb": round(total_comp_kb, 2),
                "total_saved_kb": total_saved_kb,
                "overall_ratio_percent": overall_pct,
                "saved_percentage": round(100 - overall_pct, 2) if total_orig_kb > 0 else 0.0,
                "details": file_results
            }

        finally:
            if clean_temp_dirs:
                clean_directory(download_dir)
                clean_directory(compressed_dir)


@mcp.tool()
def compress_local_file(input_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Compresses a local PDF, image, or video file using the internal routing engine.
    Returns metrics on size reduction, space saved, and duration.
    """
    if not os.path.exists(input_path):
        return {"success": False, "error": f"Input file not found: '{input_path}'"}

    if not output_path:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_cmp{ext}"

    with redirect_stdout_to_stderr():
        res = route_compress(input_path, output_path)

    saved_kb = round(res.original_size - res.compressed_size, 2) if res.compression_success else 0.0
    return {
        "success": res.compression_success,
        "file_name": res.file_name,
        "input_path": input_path,
        "output_path": output_path,
        "original_size_kb": res.original_size,
        "compressed_size_kb": res.compressed_size,
        "saved_space_kb": saved_kb,
        "compressed_percentage": res.get_compression_percentage(),
        "saved_percentage": round(100.0 - res.get_compression_percentage(), 2) if res.compression_success else 0.0,
        "duration_seconds": round(res.compression_duration, 2),
        "error_message": res.error_message
    }


def main():
    """Runs the MCP server over standard I/O."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
