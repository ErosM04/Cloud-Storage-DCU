# Cloud-Storage-DCU
Python script to retrieve PDF files from Google Drive folders, compress them with [GhostScript](https://www.ghostscript.com/) and re-upload them back to Google Drive.

The upload functionality (if used) will override the content of the original Google Drive PDF with the content of its compressed version, thus preserving the original ID.

> [!NOTE]
This script and its guide were created and tested only on a Windows system, so they probably won't work on other systems. 


## Index
1. [Setup](#setup)
    - 1.1 [**GDrive-PDF-Compressor**](#gdrive-pdf-compressor-1)
    - 1.2 [Python](#python)
    - 1.3 [GhostScript](#ghostscript)
    - 1.4 [Google Cloud project](#google-cloud-project)
2. [How To Use](#how-to-use)
    - 2.1 [Provide the folders IDs](#provide-the-folders-ids)
    - 2.2 [Run the script](#run-the-script)
    - 2.3 [Examples](#examples)
3. [Common Errors](#common-errors)


## Setup


### GDrive-PDF-Compressor
Download this Python project either by clicking on ``Code > Download ZIP`` (then extract the content) or if you have **Git** installed on your terminal run:
```shell
git clone https://github.com/ErosM04/Gdrive-PDF-Compressor.git
```
You can move the **GDrive-PDF-Compressor** folder wherever you want.


### Python
Install Python from the [website](https://www.python.org/downloads/):snake: or by using your local package manager.
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


### GhostScript
Install the compression tool [GhostScript AGPL](https://ghostscript.com/releases/gsdnld.html) and then go to ``Modify System Environment Variables > Environment Variables > PATH`` and add the following line:
```
C:\Program Files\gs\gs{version}\bin
```
Note that this path may vary if you changed it during the GhostScript installation.

Then close and reopen the terminal and run the following command:
```shell
gswin64c --version
```
If you get prompted with the Ghostcript version it is installed and properly working for our use case. Eventually you can try with ``gs --version``. If this is the case you may need to change the command used by the script, see [Common Errors](#common-errors).


### Google Cloud project
Open the terminal and update pip (Python package manager) by running:
```shell
python.exe -m pip install --upgrade pip
```
Then install the Google OAuth libraries by running:
```shell
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

> [!WARNING]
You must use a **18+** Google Account to perform the following step.

Go to the [Google Cloud Console](https://console.cloud.google.com/) and login with the same Google account linked with the Google Drive files you want to compress.

Then:
1. Create a new project.
2. From the right panel go to ``APIs & Services > Library``, search for **"Google Drive API"**, select it and click **Enable**.
3. Go to ``APIs & Services > Credentials`` and create **OAuth client ID** credentials (choose **"Desktop app"**).
4. Download the JSON file, rename it to ``credentials.json`` and place it in the **GDrive-PDF-Compressor** folder.


## How To Use


### Provide the folders IDs
To use the script you first need to get the Google Drive folder ID. To get it just open your Google Drive folder on your browser and copy the number contained at the end of the URL.

Example: If URL is https://drive.google.com/drive/folders/1A2Bv3C4dz5E6F, the ID is **``1A2Bv3C4dz5E6F``**.

To provide the folder ID to the script you have 2 ways:
1. Passing it as a parameter when you run the script, e.g.:
    ```shell
    py .\main.py 1A2Bv3C4dz5E6F
    ```
    Note: This won't just provide the ID to the scipt, it will also run it.

2. Passing more than one ID by creating a file in the **GFrive-PDF-Compressor** folder called ``folder_ids.json`` with the following structure:
    ```json
    {
        "ids": [
            "1A2Bv3C4dz5E6F",
            "1A5Pv6tDFqfSMP",
            "1A50XbuVv6tvwB"
        ]
    }
    ```
    Note: If you already specified an ID in the command, the IDs contained in the file won't be used.


### Run the script
To finally run the script open the terminal, move to the **GFrive-PDF-Compressor** folder and run the following command (don't insert the ID if you want to use the ``folder_ids.json`` file):
```shell
py .\main.py 1A2Bv3C4dz5E6F
```

If any error shows up I suggest you to check [Common Erros](#common-errors) for a solution. 

You can also use various functions by adding the parameters to the command. To list them just run:
```shell
py .\main.py --help
```

This are the parameters:
- ``-c``, ``--clean``: Delete the existing ``downloads`` and ``compressed`` folder before starting.
- ``-r``, ``--recursive``: Recursively search and download files from all subfolders.
- ``--rd``, ``--recursive-depth`` ``RD``: Recursively search and download files from all subfolders with given depth (``RD``).
- ``-u``, ``--upload``: Uploads the compressed file to its orginal position to Google Drive. The script overwrites the orginal file with its compressed version, thus preserving the orginal ID.
- ``--pf``, ``--pdfs-first``: Before diving into subfolders, process all the PDF files in the current folder.
- ``-n``, ``--number-of-files`` ``NUMBER_OF_FILES``: Set the amount of file that can be processed (``NUMBER_OF_FILES``) for each given folder ID. After the limit is reached the program stops processing the folder.
- ``-d``, ``--delete``: Deletes all downloaded and compressed files after successfully completing the upload. This will work only if the upload is enabled (with ``-u``). If any compression or upload fails no file will be eliminated.
- ``-dd``, ``--delete-downloads``: Deletes all downloaded files after successfully completing the compression or the upload. If any compression or upload fails no file will be eliminated.
- ``-dc``, ``--delete-compressed``: Deletes all compressed files after successfully completing the upload. This will work only if the upload is enabled (with ``-u``). If any compression or upload fails no file will be eliminated.
- ``-t``, ``--thread-count`` ``THREAD_COUNT``: Set the amount of cores (``THREAD_COUNT``) to use (each managing a different thread) for asynchronous compression and upload. The default value is 4 as it is safe for most CPUs (in order not to overload them).


### Examples
Here are some examples to better understand how to use the script:
- Download and compress all the (PDF) files in the given folder: 
    ```shell
    py .\main.py 1A2Bv3C4dz5E6F
    ```
- Download and compress all the files in the given folder, plus all the files contained in the subfolders: 
    ```shell
    py .\main.py 1A2Bv3C4dz5E6F -r
    ```
    If you use the recurse functionality avoid inserting in ``folder_ids.json`` a folder that is already a subfolder of another one you inserted (in ``folder_ids.json``) or you will process the same files 2 times. 

- Remove the previously downloaded and compressed files and then download and compress all the files in the given folder, plus all the files contained in the subfolders: 
    ```shell
    py .\main.py 1A2Bv3C4dz5E6F -c -r
    ```
- Remove the previously downloaded and compressed files and then download and compress all the files in the given folder, plus all the files contained in the subfolders, but it won't open more then 3 subfolders sequentially (e.g.: ``StartingFolder > SubF1 > SubF2 > SubF3``): 
    ```shell
    py .\main.py 1A2Bv3C4dz5E6F -c --rd 3
    ```
- Remove the previously downloaded and compressed files and then download, compress and upload all the files in the given folder (and subfolders): 
    ```shell
    py .\main.py 1A2Bv3C4dz5E6F -c -r -u
    ```
> [!WARNING] 
The ``-u`` parameter will override the orginal PDF files in Google Drive, ensure the level of compression used by the script won't make the smaller text unreadable. You can always find the original files in the ``downloads`` folder (in the **GDrive-PDF-Compresor** directory), unless you run the script with the ``-d`` or ``-dd`` parameters.

- Same as before but don't process more than 10 PDFs and for every folder process all the PDFs fist and then open the subfolders: 
    ```shell
    py .\main.py 1A2Bv3C4dz5E6F -c -r -u -n 10 --pf
    ```
- Remove the previously downloaded and compressed files and download, compress and upload all the files in the given folder (and subfolders), then delete all the downloaded and compressed files: 
    ```shell
    py .\main.py 1A2Bv3C4dz5E6F -c -r -u -d
    ```
- Remove the previously downloaded and compressed files and then download and compress all the files in the given folder (and subfolders) using 6 threads for the asynchronous compression: 
    ```shell
    py .\main.py 1A2Bv3C4dz5E6F -c -r -t 6
    ```


## Common Errors
Here are some common errors that can occur during the execution:

- If you get prompted with a **Request** related error just delete the ``token.json`` file. This happens because the Google Cloud project has the OAuth consent screen set to **"Testing"** mode, meaning it automatically expires after 7 days. To fix this permanently go to the ``Google Cloud Console > Navigate to APIs & Services > OAuth consent`` screen and click ``Publish App`` under ``Publishing status`` to push it to production. (Since it's just a local desktop script, it won't actually be published to the public or require a Google review).

- If the scipt prompts an error while trying to fetch the files from Google Drive it's probably because you didn't enable the **Google Drive API** on your Google Cloud prject. Just click the link in the error and it will open a web page to enable the API, just click ``Enable``. Then (as the error says) wait a few minutes for the change to be propageted on all the Google's servers.

- If ``gswin64c`` is not recognized as a command, ensure the GhostScript setup is correct ([here](#ghostscript)). Alternatively your system may not use ``gswin64c`` as command to run GhostScript, thus you need to change the following line in ``compressor.py``:
    ```python
    ghostscript_cmd = "gswin64c"
    ```
    To:
    ```python
    ghostscript_cmd = "gs"
    ```

- If the ``downloads`` and ``compressed`` folders in the **GDrive-PDF-Compressor** directory are causing any problems remove them manually or by running the script with the ``-r`` parameter.
