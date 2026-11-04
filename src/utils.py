import shutil
import os


def clean_directory(directory):
        """Removes the given directory and its content."""
        print(f"Removing '{directory}' folder...")
        
        if os.path.exists(directory):
            shutil.rmtree(directory)

        print("Folder removed")


def format_duration(duration):
    """Formats a number to ``xxh xxm xxs``.
    If the duration is less than 1 second, it will be formatted to ``xx.xxs``."""
    if duration > 1:
        duration = int(duration)
    else:
        return f"{round(duration, 2)}s"
    if duration < 60:
        return f"{duration}s"
    elif duration < 3600:
        minutes = int(duration // 60)
        seconds = duration % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = duration % 60
        return f"{hours}h {minutes}m {seconds}s"