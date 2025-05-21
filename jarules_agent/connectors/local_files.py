import os
from typing import List

def list_files(directory_path: str) -> List[str]:
    """
    Lists files and subdirectories within a given directory.

    Args:
        directory_path: The path to the directory.

    Returns:
        A list of names of files and subdirectories.

    Raises:
        FileNotFoundError: If the directory does not exist.
    """
    if not os.path.exists(directory_path):
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    if not os.path.isdir(directory_path):
        raise NotADirectoryError(f"Not a directory: {directory_path}")
    return os.listdir(directory_path)

def read_file(file_path: str) -> str:
    """
    Reads the content of a file.

    Args:
        file_path: The path to the file.

    Returns:
        The content of the file as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    if not os.path.isfile(file_path):
        # This case should ideally be different from FileNotFoundError,
        # but for now, we'll keep it simple.
        raise FileNotFoundError(f"Not a file: {file_path}")
    with open(file_path, 'r') as f:
        return f.read()

def write_file(file_path: str, content: str) -> None:
    """
    Writes content to a file. Creates the file if it doesn't exist,
    overwrites it if it does.

    Args:
        file_path: The path to the file.
        content: The string content to write to the file.

    Raises:
        IOError: If an error occurs during file writing.
    """
    try:
        # Ensure parent directory exists
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            
        with open(file_path, 'w') as f:
            f.write(content)
    except IOError as e:
        # Basic error handling, could be expanded
        print(f"Error writing to file {file_path}: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred while writing to {file_path}: {e}")
        raise
