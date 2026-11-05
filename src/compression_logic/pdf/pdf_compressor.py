import os
import time
import subprocess
import shutil
import threading

from processed_file_data import ProcessedFileData

print_lock = threading.Lock()


def get_ghostscript_command():
    """Finds the available Ghostscript executable on the system."""
    for cmd in ["gswin64c", "gswin32c", "gs"]:
        if shutil.which(cmd):
            return cmd
    return "gswin64c"  # Default fallback


def compress_pdf(input_path, output_path, start_spacing):
    """
    Compresses a PDF file using Ghostscript.
    Returns ProcessedFileData containing duration, sizes, and status.
    """
    ghostscript_cmd = get_ghostscript_command()

    # Ghostscript PDFSETTINGS levels:
    # /screen   (lowest resolution, smallest size)
    # /ebook    (medium resolution, balanced quality)
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

    start = time.time()
    try:
        subprocess.run(command, check=True)

        original_size = round(os.path.getsize(input_path) / 1024, 2)
        compressed_size = round(os.path.getsize(output_path) / 1024, 2)

        return ProcessedFileData(
            file_name=os.path.basename(output_path),
            original_size=original_size,
            compressed_size=compressed_size,
            compression_duration=time.time() - start,
            compression_success=True,
            start_spacing=start_spacing + "  "
        )

    except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
        original_size = round(os.path.getsize(input_path) / 1024, 2) if os.path.exists(input_path) else 0
        return ProcessedFileData(
            file_name=os.path.basename(output_path),
            original_size=original_size,
            compressed_size=0,
            compression_duration=time.time() - start,
            compression_success=False,
            error_message=e,
            start_spacing=start_spacing + "  "
        )
