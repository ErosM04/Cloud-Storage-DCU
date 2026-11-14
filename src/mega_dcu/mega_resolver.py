"""
MEGA Node & Folder Resolution Utilities.

Handles node inspection, display name extraction/sanitization, full path reconstruction,
trash/rubbish bin filtering, and user folder input resolution (by handle, URL, or name).
"""

import json


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
