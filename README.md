# Cloud-Storage-DCU
Python script to retrieve files (PDFs, images, and videos) from Google Drive or MEGA cloud storage folders, compress them with dedicated compression engines ([Ghostscript](https://www.ghostscript.com/) for PDFs, [Pillow](https://python-pillow.org/) for images, and [FFmpeg](https://ffmpeg.org/) with GPU acceleration for videos), and re-upload them back to the cloud.

The upload functionality (if used) will:
- **Google Drive**: Overwrite the content of the original Google Drive file with the compressed version, preserving the original file ID, links, and MIME type.
- **MEGA**: Replace the original uncompressed file in the folder (default) or keep both files by appending `" cmp"` to the compressed filename (using `--keep-original` / `-kb`).

> [!NOTE]
> This script and its guide were created and tested on Windows, with automatic hardware GPU acceleration detection (NVIDIA NVENC, Intel Quick Sync, AMD AMF) and CPU software fallback. 


## Index
1. [Setup](#setup)
    - 1.1 [**Cloud-Storage-DCU**](#cloud-storage-dcu-1)
    - 1.2 [Python](#python)
    - 1.3 [Ghostscript (PDF Compression)](#ghostscript-pdf-compression)
    - 1.4 [Pillow & FFmpeg (Image & Video Compression)](#pillow--ffmpeg-image--video-compression)
    - 1.5 [Google Drive Setup (Optional)](#google-drive-setup-optional)
    - 1.6 [MEGA Setup (Optional)](#mega-setup-optional)
2. [File Extensions Configuration](#file-extensions-configuration)
    - 2.1 [Option 1: Command-Line Flag (`-e` / `--ext`)](#option-1-command-line-flag--e----ext)
    - 2.2 [Option 2: Fallback File (`extension.json`)](#option-2-fallback-file-extensionjson)
3. [How To Use](#how-to-use)
    - 3.1 [Command Structure](#command-structure)
    - 3.2 [Provide the Folders IDs / Handles](#provide-the-folders-ids--handles)
    - 3.3 [Parameters & Options](#parameters--options)
    - 3.4 [Examples](#examples)
4. [Project Architecture](#project-architecture)
5. [Common Errors](#common-errors)


## Setup


### Cloud-Storage-DCU
Download this Python project either by clicking on ``Code > Download ZIP`` (then extract the content) or if you have **Git** installed on your terminal run:
```shell
git clone https://github.com/ErosM04/Cloud-Storage-DCU.git
```


### Python
Install Python from the [website](https://www.python.org/downloads/) :snake: or by using your local package manager.
Then open the terminal and run the following command:
```shell
python --version
```

If you get prompted with an error, instead of the version, go to ``Modify System Environment Variables > Environment Variables > PATH`` then, one by one, add the following lines (change {username} and {version} with yours):
```
C:\Users\{username}\AppData\Local\Programs\Python\Python{version}\Scripts\
C:\Users\{username}\AppData\Local\Programs\Python\Python{version}\
C:\Users\{username}\AppData\Local\Programs\Python\Launcher\
```
Then save and reopen the terminal to verify that the command works.


### Ghostscript (PDF Compression)
Install the compression tool [Ghostscript AGPL](https://ghostscript.com/releases/gsdnld.html) and then go to ``Modify System Environment Variables > Environment Variables > PATH`` and add the following line:
```
C:\Program Files\gs\gs{version}\bin
```
Note that this path may vary if you changed it during the Ghostscript installation.

Then close and reopen the terminal and run the following command:
```shell
gswin64c --version
```
If you get prompted with the Ghostscript version it is installed and properly working for our use case.


### Pillow & FFmpeg (Image & Video Compression)
To compress images and videos:
1. **Pillow** (Images: JPEG, PNG, WEBP, GIF, TIFF, BMP, etc.):
   ```shell
   py -m pip install Pillow
   ```
   *(Optional for HEIC/AVIF: `py -m pip install pillow-heif`)*
2. **FFmpeg** (Videos: MP4, MKV, MOV, AVI, WEBM, etc. with GPU acceleration):
   Ensure `ffmpeg` is installed and available in your `PATH`.
   Check it with:
   ```shell
   ffmpeg -version
   ```
   The video compressor automatically detects hardware GPU encoders (`h264_nvenc` for NVIDIA, `h264_qsv` for Intel Quick Sync, `h264_amf` for AMD, `h264_mf` for MediaFoundation) and seamlessly falls back to CPU `libx264` if no GPU encoder is supported.


### Google Drive Setup (Optional)
If you plan to use Google Drive:
```shell
py -m pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

> [!WARNING]
> You must use a **18+** Google Account to perform the following step.

Go to the [Google Cloud Console](https://console.cloud.google.com/) and login with the same Google account linked with the Google Drive files you want to compress.

Then:
1. Create a new project.
2. From the project's panel go to ``APIs & Services > Library``, search for **"Google Drive API"**, select it and click **Enable**.
3. Go to ``APIs & Services > Credentials`` and configure the **consent screen** if asked.
4. Create **OAuth client ID** credentials (choose **"Desktop app"**).
5. Download the JSON file, rename it to ``credentials.json`` and place it in the root folder of this project (not in ``/src``!!).
6. In the project's panel go to ``Google Auth Platoform > Public`` and add your email to the **Test users**.


### MEGA Setup (Optional)
If you plan to use MEGA:
```shell
py -m pip install mega.py pycryptodome tenacity
```
*No API console setup is required for MEGA!* When running the script with `mega`, it will prompt for your MEGA account email and password directly in the terminal (with hidden password input). You can also optionally set `MEGA_EMAIL` and `MEGA_PASSWORD` environment variables.


## File Extensions Configuration
You can specify which file types (PDF, PNG, JPG, MP4, etc.) the program should download and compress using two methods:

### Option 1: Command-Line Flag (`-e` / `--ext`)
Pass the exact extension names directly in the execution command:
```shell
# Single extension:
py .\src\main.py drive FolderID -e pdf

# Multiple extensions (space-separated or comma-separated):
py .\src\main.py mega FolderName -e pdf png jpg mp4
py .\src\main.py drive FolderID -e "pdf,png,webp"
```

### Option 2: Fallback File (`extension.json`)
If no `-e` / `--ext` parameter is passed in the command line, the program automatically falls back to reading `extension.json` located in the project root:
```json
{
  "extensions": [
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "mp4",
    "mkv",
    "mov"
  ]
}
```
*(Or simply a JSON array: `["pdf", "png", "mp4"]`).*

If neither the CLI flag nor `extension.json` is specified, the script defaults to operating on all supported extensions.


## How To Use


### Command Structure
Run the script by choosing the provider (`drive` or `mega`):
```shell
py .\src\main.py drive [folder_id] [options]
py .\src\main.py mega [folder_id_or_name] [options]
```


### Provide the Folders IDs / Handles

#### For Google Drive:
Open your Google Drive folder on your browser and copy the ID at the end of the URL.
* Example: URL `https://drive.google.com/drive/folders/1A2Bv3C4dz5E6F` -> ID is **``1A2Bv3C4dz5E6F``**.

#### For MEGA:
You can provide any of the following:
1. **Folder Node Handle**: 8-character string ID (e.g. `k0k3TBwD`).
2. **Folder Name**: Name of the folder in your MEGA account (e.g. `Invoices` or `MyFolder`).
3. **Root**: Use `root` to target your entire MEGA Cloud Drive.

#### Passing multiple IDs via `folder_ids.json`:
If you omit the folder ID from the command, the script reads from `folder_ids.json`. You can organize them by provider:
```json
{
    "drive": [
        "1A2Bv3C4dz5E6F",
        "1A5Pv6tDFqfSMP"
    ],
    "mega": [
        "k0k3TBwD",
        "Invoices"
    ]
}
```
*(Or keep the classic `"ids": ["..."]` format, which works as a fallback).*


### Parameters & Options

#### Common Parameters (Drive & MEGA):
- `-e`, `--ext`, `--extension`, `--extensions`: Specify one or more file extensions to operate on (e.g. `-e pdf` or `-e png jpg mp4`). If omitted, reads from `extension.json`.
- `-c`, `--clean`: Delete existing downloaded and compressed folders before starting (`downloads_drive`/`compressed_drive` for Google Drive or `downloads_mega`/`compressed_mega` for MEGA).
- ``-r``, ``--recursive``: Recursively search and download files from all subfolders.
- ``--rd``, ``--recursive-depth`` ``RD``: Recursively search and download files from all subfolders up to a given depth (``RD``).
- ``-u``, ``--upload``: Uploads the compressed files back to cloud storage.
- ``--pf``, ``--pdfs-first``: Process all files in the current folder before diving into subfolders.
- ``-n``, ``--number-of-files`` ``N``: Limit the maximum amount of files processed.
- ``-d``, ``--delete``: Deletes all downloaded and compressed files after successful upload (requires ``-u``).
- ``-dd``, ``--delete-downloads``: Deletes all downloaded files after successful compression or upload.
- ``-dc``, ``--delete-compressed``: Deletes all compressed files after successful upload (requires ``-u``).
- ``-t``, ``--thread-count`` ``T``: Number of threads for asynchronous compression and upload (default: 4).

#### MEGA-Specific Parameters:
- ``--keep-original``, ``--keep-both``, ``-kb``: Keeps both the original uncompressed file and the compressed file on MEGA. The compressed version will be uploaded with `" cmp"` appended to its name (e.g. `document cmp.pdf`). Without this flag, the script deletes the original uncompressed file from MEGA upon successful upload (replacing it).
- ``--cmp-suffix`` ``SUFFIX``: Custom suffix to append when `--keep-original` is used (default: `' cmp'`).


### Examples

#### Google Drive Examples:
- Download and compress all targeted files in a Drive folder:
    ```shell
    py .\src\main.py drive 1A2Bv3C4dz5E6F
    ```
- Compress only images (PNG, JPG) and videos (MP4):
    ```shell
    py .\src\main.py drive 1A2Bv3C4dz5E6F -e png jpg mp4 -r
    ```
- Recursive processing with upload and cleanup:
    ```shell
    py .\src\main.py drive 1A2Bv3C4dz5E6F -c -r -u -d
    ```

#### MEGA Examples:
- Download and compress all targeted files from a MEGA folder:
    ```shell
    py .\src\main.py mega Invoices -r
    ```
- Target only PDF and WEBP files:
    ```shell
    py .\src\main.py mega Invoices -e pdf webp -r
    ```
- Download, compress, and replace original files on MEGA:
    ```shell
    py .\src\main.py mega Invoices -c -r -u
    ```
- Download, compress, and upload without deleting original files (appends " cmp" to the compressed file):
    ```shell
    py .\src\main.py mega Invoices -c -r -u -kb
    ```
- Process from `folder_ids.json` using 6 threads:
    ```shell
    py .\src\main.py mega -r -u -t 6
    ```


## Project Architecture
The project is structured with modularity as a primary goal:
```
Cloud-Storage-DCU/
├── extension.json                    # Default target file extensions (fallback)
├── folder_ids.json                   # Cloud folder IDs configuration
├── src/
│   ├── main.py                       # CLI entry point and provider dispatcher
│   ├── flags.py                      # Argument parser (-e, -c, -r, -u, etc.)
│   ├── utils.py                      # Extension resolver, statistics, cleanup
│   ├── processed_file_data.py        # Standardized file compression result class
│   ├── compression_logic/            # Modular compression engine
│   │   ├── route_compression.py      # Central extension-based router
│   │   ├── pdf/
│   │   │   └── pdf_compressor.py     # Ghostscript PDF compression
│   │   ├── image/
│   │   │   └── image_compressor.py   # Pillow image compression (JPEG, PNG, WEBP, etc.)
│   │   └── video/
│   │       └── video_compressor.py   # FFmpeg video compression with GPU acceleration
│   ├── drive/                        # Google Drive module
│   │   ├── drive_auth.py             # OAuth2 authentication
│   │   ├── drive_downloader.py       # Async downloader calling route_compression
│   │   ├── drive_uploader.py         # In-place file updater with dynamic MIME detection
│   │   └── drive_main.py             # Google Drive orchestration
│   └── mega_dcu/                     # MEGA cloud module
│       ├── mega_auth.py              # MEGA authentication prompt
│       ├── mega_downloader.py        # Chunked downloader calling route_compression
│       ├── mega_uploader.py          # Uploader with optional original file retention
│       └── mega_main.py              # MEGA orchestration
```

### Compression Routing Workflow
1. The downloader (`drive_downloader.py` or `mega_downloader.py`) receives a downloaded file.
2. It invokes `route_compress(input_path, output_path)` in `src/compression_logic/route_compression.py`.
3. `route_compression.py` inspects the file extension:
   - `.pdf` -> dispatched to `src/compression_logic/pdf/pdf_compressor.py`
   - `.png`, `.jpg`, `.jpeg`, `.webp`, `.tiff`, etc. -> dispatched to `src/compression_logic/image/image_compressor.py`
   - `.mp4`, `.mkv`, `.mov`, `.avi`, etc. -> dispatched to `src/compression_logic/video/video_compressor.py`
4. The compressor returns a unified `ProcessedFileData` object containing the duration, original size, compressed size, and compression success status.


## Common Errors
- **Request related error (Google Drive)**: Delete `token.json` and publish your OAuth app to Production mode in Google Cloud Console.
- **Account access to project denied (Google Cloud Console)**: Go to the Google Cloude Console and open the preject you created, then in the project's panel go to ``Google Auth Platoform > Public`` and add your email to the **Test users**.
- **Google Drive API not enabled**: Enable the Google Drive API in Google Cloud Console.
- **Ghostscript command not found**: Ensure `gswin64c` is in PATH. If on Linux/macOS or your binary is named `gs`, change `ghostscript_cmd = "gswin64c"` to `"gs"` in `src/compressor.py`.
- **MEGA Login Failed**: Ensure your MEGA email and password are correct.
