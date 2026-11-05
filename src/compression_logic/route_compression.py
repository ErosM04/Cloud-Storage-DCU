import os
import sys

# Ensure src directory is in sys.path for direct invocations
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

try:
    from processed_file_data import ProcessedFileData
except ImportError:
    from src.processed_file_data import ProcessedFileData

try:
    from compression_logic.pdf.pdf_compressor import compress_pdf
    from compression_logic.image.image_compressor import compress_image
    from compression_logic.video.video_compressor import compress_video
except ImportError:
    from pdf.pdf_compressor import compress_pdf
    from image.image_compressor import compress_image
    from video.video_compressor import compress_video


PDF_EXTENSIONS = {'.pdf'}

IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.jpe', '.png', '.webp', '.bmp', '.dib',
    '.tiff', '.tif', '.gif', '.ico', '.ppm', '.pgm', '.pbm', '.pnm',
    '.tga', '.heic', '.heif', '.avif'
}

VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.qt', '.wmv', '.flv',
    '.webm', '.m4v', '.mpg', '.mpeg', '.m2v', '.ts', '.mts',
    '.m2ts', '.3gp', '.3g2'
}


def normalize_ext(extension: str) -> str:
    """Normalizes an extension string (e.g. '.PNG', ' JPG ' -> 'png', 'jpg')."""
    if not extension:
        return ""
    return extension.strip().lstrip('.').lower()


def extract_extension(filename_or_ext: str) -> str:
    """Extracts a clean, normalized extension without dot from a filename, path, or extension string."""
    if not filename_or_ext:
        return ""
    s = str(filename_or_ext).strip()
    # If passed as '.png' or 'png'
    if s.startswith('.') and s.count('.') == 1:
        return s.lstrip('.').lower()
    _, ext = os.path.splitext(s)
    if ext:
        return ext.lstrip('.').lower()
    return s.lstrip('.').lower()


def get_all_supported_extensions():
    """Returns a set of all supported file extensions without leading dots."""
    all_exts = set()
    for ext_set in (PDF_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS):
        for e in ext_set:
            all_exts.add(e.lstrip('.').lower())
    return all_exts


def get_category_for_extension(filename_or_ext: str):
    """
    Returns the category ('pdf', 'image', 'video') for a given extension or filename,
    or None if unsupported.
    """
    clean = extract_extension(filename_or_ext)
    if not clean:
        return None
    norm = '.' + clean
    if norm in PDF_EXTENSIONS:
        return 'pdf'
    if norm in IMAGE_EXTENSIONS:
        return 'image'
    if norm in VIDEO_EXTENSIONS:
        return 'video'
    return None


def is_supported_extension(filename_or_ext: str) -> bool:
    """Checks whether the file extension is supported by any compressor."""
    return get_category_for_extension(filename_or_ext) is not None


def is_file_eligible(filename: str, allowed_extensions=None) -> bool:
    """
    Determines if a given filename matches the allowed extensions.
    If allowed_extensions is None or empty, checks if the file has any supported extension.
    """
    clean_ext = extract_extension(filename)
    if not clean_ext:
        return False

    if allowed_extensions is not None and len(allowed_extensions) > 0:
        normalized_allowed = {normalize_ext(e) for e in allowed_extensions if e}
        return clean_ext in normalized_allowed

    # Fallback to checking if it is supported at all
    return is_supported_extension(clean_ext)


def route_compress(input_path: str, output_path: str, start_spacing: str = "") -> ProcessedFileData:
    """
    Routes compression to the appropriate compressor script (pdf, image, video)
    based on the file extension.
    Returns ProcessedFileData.
    """
    ext = os.path.splitext(input_path)[1].lower()
    category = get_category_for_extension(ext)

    if category == 'pdf':
        return compress_pdf(input_path, output_path, start_spacing)
    elif category == 'image':
        return compress_image(input_path, output_path, start_spacing)
    elif category == 'video':
        return compress_video(input_path, output_path, start_spacing)
    else:
        orig = round(os.path.getsize(input_path) / 1024, 2) if os.path.exists(input_path) else 0
        return ProcessedFileData(
            file_name=os.path.basename(output_path),
            original_size=orig,
            compressed_size=0,
            compression_duration=0,
            compression_success=False,
            error_message=f"Unsupported file extension: '{ext}'",
            start_spacing=start_spacing + "  "
        )


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Compress file by routing to specific compressor based on extension.")
    parser.add_argument("input", help="Path to input file")
    parser.add_argument("-o", "--output", help="Path to output file", default=None)
    parser.add_argument("-s", "--spacing", help="Indentation spacing for prints", default="")
    args = parser.parse_args()

    out_file = args.output
    if not out_file:
        base, ext = os.path.splitext(args.input)
        out_file = f"{base}_compressed{ext}"

    result = route_compress(args.input, out_file, args.spacing)
    from utils import print_compression_result
    print_compression_result(result)
