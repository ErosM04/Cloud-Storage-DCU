import os
import time
import subprocess
import threading

from processed_file_data import ProcessedFileData


# A lock to prevent background threads from fucking up terminal text when printing
print_lock = threading.Lock()


def compress_pdf_ghostscript(input_path, output_path, start_spacing):
    """Compresses a PDF file using Ghostscript.
    If the compression succeded returns informations about the compression task."""
    # Note: If you are on Windows, change "gs" to "gswin64c"
    ghostscript_cmd = "gswin64c"

    # Ghostscript PDFSETTINGS levels:
    # /screen   (lowest resolution, smallest size)
    # /ebook    (medium resolution)
    # /printer  (high resolution)
    # /prepress (highest resolution, preserves colors)

    command = [
        ghostscript_cmd,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dPDFSETTINGS=/ebook", 
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        input_path
    ]
    
    try:
        start = time.time()
        subprocess.run(command, check=True) # Compress the PDF using the Ghostscript command
        
        return ProcessedFileData(file_name=os.path.basename(output_path),
                                   original_size= round((os.path.getsize(input_path) / 1024), 2),
                                   compressed_size=round((os.path.getsize(output_path) / 1024), 2),
                                   compression_duration= time.time() - start,
                                   compression_success=True,
                                   start_spacing=start_spacing+"  ")
        
    except subprocess.CalledProcessError as e:
        return ProcessedFileData(file_name=os.path.basename(output_path),
                                   original_size= round((os.path.getsize(input_path) / 1024), 2),
                                   compression_duration= time.time() - start,
                                   compression_success=False,
                                   error_message=e,
                                   start_spacing=start_spacing+"  ")

    except FileNotFoundError:
        return ProcessedFileData(file_name=os.path.basename(output_path),
                                   compression_success=False,
                                   error_message=e,
                                   start_spacing=start_spacing+"  ")