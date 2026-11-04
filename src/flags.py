import argparse


def get_args():
    """Setup and returns the command line argument parser"""
    parser = argparse.ArgumentParser(description="Download, asynchronously compress and re-upload PDFs from Google Drive folders.")

    setup_flags(parser)

    return parser.parse_args()


def setup_flags(parser: argparse.ArgumentParser):
    """Setup all the flags for the script arguments. Can be listed with '--help'."""
    
    # positional argument for folder ID
    parser.add_argument('folder_id',
                        nargs='?', # '1' = One, '?' = One ore None.
                        default=None, 
                        help="The Google Drive folder ID. If omitted, reads from the default file ('folder_ids.json').")

    # -c / --clean flag
    parser.add_argument('-c', '--clean', 
                        action='store_true', # treats the argument as a boolean itself, or the command to run the script would be: "py .\main.py -r True" 
                        help="Delete the existing 'downloads' and 'compressed' folder before starting.")
    
    # -r / --recursive flag
    parser.add_argument('-r', '--recursive', 
                        action='store_true',
                        help="Recursively search and download files from all subfolders.")
   
    # --rd / --recursive-depth flag
    parser.add_argument('--rd', '--recursive-depth', 
                        type=int,
                        help="Recursively search and download files from all subfolders with given depth.")
    
    # -u / --upload flag
    parser.add_argument('-u', '--upload', 
                        action='store_true',
                        help="Uploads the compressed file to its orginal position to Google Drive. "
                        "The script overwrites the orginal file with its compressed version, thus preserving the orginal ID.")
    
    # --pf / --pdfs-first flag
    parser.add_argument('--pf', '--pdfs-first', 
                        action='store_true',
                        help="Before diving into subfolders, process all the PDF files in the current folder.")

    # -n / --number-of-files flag
    parser.add_argument('-n', '--number-of-files',
                        type=int,
                        help="Set the amount of file that can be processed for each given folder ID. After the limit is reached "
                        "the program stops processing the folder.")
    
    # -d / --delete flag
    parser.add_argument('-d', '--delete', 
                        action='store_true',
                        help="Deletes all downloaded and compressed files after successfully completing the upload. "
                        "This will work only if the upload is enabled (with '-u'). "
                        "If any compression or upload fails no file will be eliminated.")
    
    # -dd / --delete-downloads flag
    parser.add_argument('-dd', '--delete-downloads', 
                        action='store_true',
                        help="Deletes all downloaded files after successfully completing the compression or the upload. "
                        "If any compression or upload fails no file will be eliminated.")
    
    # -dc / --delete-compressed flag
    parser.add_argument('-dc', '--delete-compressed', 
                        action='store_true',
                        help="Deletes all compressed files after successfully completing the upload. "
                        "This will work only if the upload is enabled (with '-u'). "
                        "If any compression or upload fails no file will be eliminated.")
    
    # -t / --thread-count flag
    parser.add_argument('-t', '--thread-count',
                        type=int,
                        default=4,
                        help="Set the amount of cores (each managing a different thread) to use for asynchronous compression and upload. "
                        "The default value is 4 as it is safe for most CPUs (in order not to overload them).")