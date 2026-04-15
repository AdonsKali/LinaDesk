import difflib
import os

def find_exe_files(directory):
    """
    Args:
        directory (str): The starting directory to search from.
    Returns:
        list: A list of most suitable absolute paths and launchers to found .exe files.
    """
    exe_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".exe"):
                path = os.path.join(root, file)
                folder_name = os.path.basename(os.path.dirname(path))
                file_name = os.path.splitext(os.path.basename(path))[0]
                norm_folder = folder_name.lower().replace(" ", "")
                norm_file = file_name.lower().replace(" ", "")
                similarity = difflib.SequenceMatcher(None, norm_folder, norm_file).ratio()
                if similarity > 0.67 or difflib.SequenceMatcher(None, "launcher", norm_file).ratio() > 0.55:
                    exe_paths.append(os.path.join(root, file))
    return exe_paths


def find_files(directory, extension: str):
    exe_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(f".{extension}"):
                exe_paths.append(os.path.join(root, file))
    return exe_paths

