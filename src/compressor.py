from utils import print_lock
from compression_logic.pdf.pdf_compressor import compress_pdf as compress_pdf_ghostscript
from compression_logic.route_compression import route_compress

__all__ = ['compress_pdf_ghostscript', 'route_compress', 'print_lock']
