"""
Data models for tracking file processing results.
"""


class ProcessedFileData:
    """Holds information regarding the compression and upload of a file."""

    def __init__(self, 
                 file_name: str, 
                 original_size: float, 
                 compressed_size: float, 
                 compression_duration: float, 
                 start_spacing: str, 
                 compression_success: bool,
                 error_message=None):
        """
        Initializes processing result metadata for a file.

        Args:
            file_name (str): The display filename.
            original_size (float): Pre-compression size in KB.
            compressed_size (float): Post-compression size in KB.
            compression_duration (float): Time taken to compress in seconds.
            start_spacing (str): Terminal indentation prefix.
            compression_success (bool): Whether compression succeeded.
            error_message (optional): Error details if compression failed.
        """
        self.file_name = file_name
        self.original_size = original_size
        self.compressed_size = compressed_size
        self.compression_duration = compression_duration
        self.compression_success = compression_success
        self.error_message = error_message
        self.start_spacing = start_spacing


    def get_compression_percentage(self):
        """Returns the % of space occupied by the compressed file in relation to the original file."""
        if not self.original_size or self.original_size == 0:
            return 0.0
        return round((100 * self.compressed_size) / self.original_size, 2)