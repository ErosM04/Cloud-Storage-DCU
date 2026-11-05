class ProcessedFileData:
    """Holds informations regarding the compression of a file."""

    def __init__(self, 
                 file_name, 
                 original_size, 
                 compressed_size, 
                 compression_duration, 
                 start_spacing, 
                 compression_success: bool,
                 error_message=None):
        self.file_name = file_name # Instance variable
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