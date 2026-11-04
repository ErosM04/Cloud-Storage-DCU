# Cloud-Storage-DCU
Python script to retrieve PDF files from Google Drive or MEGA cloud storage folders, compress them with [Ghostscript](https://www.ghostscript.com/) and re-upload them back to the cloud.

The upload functionality (if used) will:
- **Google Drive**: Overwrite the content of the original Google Drive PDF with the compressed version, preserving the original file ID and links.
- **MEGA**: Replace the original uncompressed file in the folder (default) or keep both files by appending `" cmp"` to the compressed filename (using `--keep-original` / `-kb`).

> [!NOTE]
> This script and its guide were created and tested only on a Windows system, so they probably won't work on other systems. 


## Index
1. [Setup](#setup)
    - 1.1 [**Cloud-Storage-DCU**](#cloud-storage-dcu-1)
    - 1.2 [Python](#python)
    - 1.3 [Ghostscript](#ghostscript)
    - 1.4 [Google Drive Setup (Optional)](#google-drive-setup-optional)
    - 1.5 [MEGA Setup (Optional)](#mega-setup-optional)
2. [How To Use](#how-to-use)
    - 2.1 [Command Structure](#command-structure)
    - 2.2 [Provide the Folders IDs / Handles](#provide-the-folders-ids--handles)
    - 2.3 [Parameters & Options](#parameters--options)
    - 2.4 [Examples](#examples)
3. [Common Errors](#common-errors)


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


### Ghostscript
Install the compression tool [Ghostscript AGPL](https://ghostscript.com/releases/gsdnld.html) and then go to ``Modify System Environment Variables > Environment Variables > PATH`` and add the following line:
```
C:\Program Files\gs\gs{version}\bin
```
Note that this path may vary if you changed it during the Ghostscript installation.

Then close and reopen the terminal and run the following command:
```shell
gswin64c --version
```
If you get prompted with the Ghostscript version it is installed and properly working for our use case. Eventually you can try with ``gs --version``. If this is the case you may need to change the command used by the script, see [Common Errors](#common-errors).


### Google Drive Setup (Optional)
If you plan to use Google Drive:
```shell
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

> [!WARNING]
> You must use a **18+** Google Account to perform the following step.

Go to the [Google Cloud Console](https://console.cloud.google.com/) and login with the same Google account linked with the Google Drive files you want to compress.

Then:
1. Create a new project.
2. From the right panel go to ``APIs & Services > Library``, search for **"Google Drive API"**, select it and click **Enable**.
3. Go to ``APIs & Services > Credentials`` and create **OAuth client ID** credentials (choose **"Desktop app"**).
4. Download the JSON file, rename it to ``credentials.json`` and place it in the root folder of this project.


### MEGA Setup (Optional)
If you plan to use MEGA:
```shell
pip install mega.py pycryptodome tenacity
```
*No API console setup is required for MEGA!* When running the script with `mega`, it will prompt for your MEGA account email and password directly in the terminal (with hidden password input). You can also optionally set `MEGA_EMAIL` and `MEGA_PASSWORD` environment variables.


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
- `-c`, `--clean`: Delete existing downloaded and compressed folders before starting (`downloads_drive`/`compressed_drive` for Google Drive or `downloads_mega`/`compressed_mega` for MEGA).
- ``-r``, ``--recursive``: Recursively search and download files from all subfolders.
- ``--rd``, ``--recursive-depth`` ``RD``: Recursively search and download files from all subfolders up to a given depth (``RD``).
- ``-u``, ``--upload``: Uploads the compressed files back to cloud storage.
- ``--pf``, ``--pdfs-first``: Process all PDF files in the current folder before diving into subfolders.
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
- Download and compress all PDFs in a Drive folder:
    ```shell
    py .\src\main.py drive 1A2Bv3C4dz5E6F
    ```
- Recursive processing with upload and cleanup:
    ```shell
    py .\src\main.py drive 1A2Bv3C4dz5E6F -c -r -u -d
    ```

#### MEGA Examples:
- Download and compress all PDFs from a MEGA folder:
    ```shell
    py .\src\main.py mega Invoices -r
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


## Common Errors
- **Request related error (Google Drive)**: Delete `token.json` and publish your OAuth app to Production mode in Google Cloud Console.
- **Google Drive API not enabled**: Enable the Google Drive API in Google Cloud Console.
- **Ghostscript command not found**: Ensure `gswin64c` is in PATH. If on Linux/macOS or your binary is named `gs`, change `ghostscript_cmd = "gswin64c"` to `"gs"` in `src/compressor.py`.
- **MEGA Login Failed**: Ensure your MEGA email and password are correct.
