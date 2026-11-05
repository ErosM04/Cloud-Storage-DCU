import os
import time
import shutil
from PIL import Image

# Optional HEIF / AVIF support if pillow_heif is installed
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

from processed_file_data import ProcessedFileData


def compress_image(input_path, output_path, start_spacing, quality=80):
    """
    Compresses an image file using Pillow across various formats (JPEG, PNG, WEBP, GIF, TIFF, BMP, etc.).
    Returns ProcessedFileData containing duration, sizes, and status.
    """
    start = time.time()
    try:
        ext = os.path.splitext(input_path)[1].lower()
        original_size = round(os.path.getsize(input_path) / 1024, 2)

        with Image.open(input_path) as img:
            save_format = img.format or ext.lstrip('.').upper()
            if save_format == 'JPG':
                save_format = 'JPEG'

            save_kwargs = {}

            if ext in ['.jpg', '.jpeg'] or save_format == 'JPEG':
                # Convert palette/transparency to standard RGB for JPEG encoding
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparent pixels
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                save_kwargs = {
                    'quality': quality,
                    'optimize': True,
                    'progressive': True
                }

            elif ext == '.png' or save_format == 'PNG':
                save_kwargs = {
                    'optimize': True,
                    'compress_level': 9
                }

            elif ext == '.webp' or save_format == 'WEBP':
                save_kwargs = {
                    'quality': quality,
                    'method': 6
                }

            elif ext in ['.tiff', '.tif'] or save_format == 'TIFF':
                save_kwargs = {
                    'compression': 'tiff_lzw'
                }

            elif ext == '.gif' or save_format == 'GIF':
                save_kwargs = {
                    'optimize': True
                }

            # Strip EXIF and save to output
            img.save(output_path, format=save_format, **save_kwargs)

        compressed_size = round(os.path.getsize(output_path) / 1024, 2)

        # Safety check: if compression somehow increased file size, keep the original
        if compressed_size > original_size:
            shutil.copy2(input_path, output_path)
            compressed_size = original_size

        return ProcessedFileData(
            file_name=os.path.basename(output_path),
            original_size=original_size,
            compressed_size=compressed_size,
            compression_duration=time.time() - start,
            compression_success=True,
            start_spacing=start_spacing + "  "
        )

    except Exception as e:
        orig = round(os.path.getsize(input_path) / 1024, 2) if os.path.exists(input_path) else 0
        return ProcessedFileData(
            file_name=os.path.basename(output_path),
            original_size=orig,
            compressed_size=0,
            compression_duration=time.time() - start,
            compression_success=False,
            error_message=e,
            start_spacing=start_spacing + "  "
        )
