# Cloud-Storage-DCU FastMCP Server

A Model Context Protocol (MCP) server providing AI agents with direct, typed tool calling access to Google Drive and MEGA cloud compression pipelines, folder inspection, and local document compression.

---

## 🛠️ Available MCP Tools

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `check_cloud_auth` | `provider` ("drive", "mega", "all") | Checks whether Google Drive and/or MEGA credentials are authenticated and valid without prompting. |
| `get_supported_file_types` | *None* | Returns supported extension lists grouped by compression engine (PDF, Image, Video). |
| `resolve_cloud_folder` | `provider`, `folder_input` | Resolves a folder name, folder ID, or 'root' to its unique cloud ID/handle and display name. |
| `list_cloud_folder_contents` | `provider`, `folder_input`, `target_extensions`, `recursive`, `max_depth` | Lists files and subfolders in a cloud folder and flags which files are eligible for compression. |
| `compress_cloud_folder` | `provider`, `folder_input`, `target_extensions`, `recursive`, `upload`, `keep_original`, etc. | Executes full end-to-end cloud file compression and returns structured metrics (bytes saved, ratios). |
| `compress_local_file` | `input_path`, `output_path` | Directly compresses a local PDF, image, or video file and returns reduction metrics. |

---

## 🚀 How to Run

### Standalone (Stdio Transport)
```bash
python -m src.mcp_server.server
```
or (if installed via pip):
```bash
dcu-mcp
```

---

## ⚙️ MCP Client Configuration

### For Google Antigravity / Gemini CLI (`mcp_config.json`):
Add the server entry to `~/.gemini/config/mcp_config.json` or `.agents/mcp_config.json`:

```json
{
  "mcpServers": {
    "cloud-storage-dcu": {
      "command": "python",
      "args": ["-m", "src.mcp_server.server"],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### For Codex (`config.toml`):
Add to `~/.codex/config.toml` (global) or `.codex/config.toml` (project-local):

```toml
[mcp_servers.cloud_storage_dcu]
enabled = true
command = "python"
args = ["-m", "src.mcp_server.server"]

[mcp_servers.cloud_storage_dcu.env]
PYTHONUNBUFFERED = "1"
```

Alternatively, register directly via the Codex CLI:
```bash
codex mcp add cloud-storage-dcu -- python -m src.mcp_server.server
```

### For Hermes Agent (`config.yaml`):
Add to `~/.hermes/config.yaml` under the `mcp_servers` section:

```yaml
mcp_servers:
  cloud_storage_dcu:
    command: "python"
    args:
      - "-m"
      - "src.mcp_server.server"
    env:
      PYTHONUNBUFFERED: "1"
    enabled: true
    timeout: 180
```

### For Claude Desktop (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "cloud-storage-dcu": {
      "command": "python",
      "args": ["C:\\path\\to\\Cloud-Storage-DCU\\src\\mcp_server\\server.py"],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

---

## 🛡️ Stdio Transport Safety
All terminal logs, progress bars, and diagnostics emitted by the underlying compression engines (Ghostscript, Pillow, Requests) are automatically routed to `sys.stderr`. Standard output (`sys.stdout`) remains 100% clean for JSON-RPC communication.
