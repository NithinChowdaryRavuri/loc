import os
import argparse
import re
from collections import defaultdict

# --- Configuration ---

# Language definitions (extension: (language_name, single_line_comment_prefix))
# Add more languages and their comment styles here
LANGUAGE_DEFINITIONS = {
    ".py": ("Python", "#"),
    ".java": ("Java", "//"),
    ".js": ("JavaScript", "//"),
    ".c": ("C", "//"),
    ".cpp": ("C++", "//"),
    ".h": ("C/C++ Header", "//"),
    ".cs": ("C#", "//"),
    ".rb": ("Ruby", "#"),
    ".go": ("Go", "//"),
    ".rs": ("Rust", "//"),
    ".html": ("HTML", None), # HTML comments are <!-- ... -->, more complex
    ".css": ("CSS", None),   # CSS comments are /* ... */, more complex
    ".php": ("PHP", "//"),
    ".swift": ("Swift", "//"),
    ".kt": ("Kotlin", "//"),
    ".ts": ("TypeScript", "//"),
    ".scala": ("Scala", "//"),
    ".pl": ("Perl", "#"),
    ".lua": ("Lua", "--"),
    ".r": ("R", "#"),
    ".sh": ("Shell Script", "#"),
    ".ps1": ("PowerShell", "#"),
}

# Default items to ignore
# Users can extend this via command-line arguments or by modifying this list
DEFAULT_IGNORE_DIRS = {".git", "venv", "node_modules", "__pycache__", ".vscode", ".idea", "build", "dist", "target", ".venv", ".next"}
DEFAULT_IGNORE_FILES = {"LICENSE", "README.md"} # Exact file names
DEFAULT_IGNORE_EXTENSIONS = {".log", ".tmp", ".bak", ".swp", ".map", ".min.js", ".min.css"} # File extensions

# --- Helper Functions ---

def get_language_and_comment_prefix(file_path):
    """Identifies the language and its single-line comment prefix from the file extension."""
    _, ext = os.path.splitext(file_path)
    return LANGUAGE_DEFINITIONS.get(ext.lower())

def count_loc_in_file(file_path, comment_prefix):
    """Counts non-empty, non-comment lines in a file."""
    loc = 0
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                stripped_line = line.strip()
                if not stripped_line:  # Skip empty lines
                    continue
                if comment_prefix and stripped_line.startswith(comment_prefix): # Skip single-line comments
                    continue
                # For HTML/CSS, we are not handling block comments here, just counting non-empty lines
                # More sophisticated parsing would be needed for accurate block comment exclusion
                loc += 1
    except Exception as e:
        print(f"Warning: Could not read file {file_path}: {e}")
        return 0
    return loc

def should_ignore(path, ignore_dirs, ignore_files, ignore_extensions):
    """Checks if a file or directory should be ignored."""
    path_name = os.path.basename(path)
    _, ext = os.path.splitext(path_name)

    if os.path.isdir(path):
        return path_name.lower() in ignore_dirs
    else: # It's a file
        if path_name in ignore_files:
            return True
        if ext.lower() in ignore_extensions:
            return True
    return False

# --- Core Logic ---

def analyze_directory(target_dir, ignore_dirs, ignore_files, ignore_extensions):
    """Analyzes the directory, counts LOC per language, and returns the stats."""
    loc_stats = defaultdict(int)
    total_files_processed = 0
    total_loc_overall = 0

    print(f"Starting analysis of directory: {target_dir}\n")

    for root, dirs, files in os.walk(target_dir, topdown=True):
        # Filter out ignored directories before further processing
        original_dirs_count = len(dirs)
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), ignore_dirs, ignore_files, ignore_extensions)]
        
        # Print the current directory being analyzed if it wasn't pruned by a parent ignore
        # and if it's not the initial target_dir (which is already printed)
        # or if it is the target_dir and it's the first iteration.
        # A more direct way is to just print `root` as it's the current directory being walked.
        print(f"Analyzing: {os.path.abspath(root)}")

        for file_name in files:
            file_path = os.path.join(root, file_name)

            if should_ignore(file_path, ignore_dirs, ignore_files, ignore_extensions):
                # print(f"Skipping ignored file: {file_path}")
                continue

            lang_info = get_language_and_comment_prefix(file_path)
            if lang_info:
                language_name, comment_char = lang_info
                # print(f"Processing {language_name} file: {file_path}")
                file_loc = count_loc_in_file(file_path, comment_char)
                if file_loc > 0:
                    loc_stats[language_name] += file_loc
                    total_loc_overall += file_loc
                    total_files_processed += 1
            # else:
                # print(f"Skipping unrecognized file type: {file_path}")

    return loc_stats, total_files_processed, total_loc_overall

# --- Reporting ---

def print_report(loc_stats, total_files_processed, total_loc_overall):
    """Prints the LOC analysis report."""
    print("\n--- LOC Analysis Report ---")
    if not loc_stats:
        print("No source code files found or processed.")
        return

    # Sort by LOC count descending
    sorted_stats = sorted(loc_stats.items(), key=lambda item: item[1], reverse=True)

    print(f"{'Language':<20} | {'Lines of Code':<15}")
    print("-" * 38)
    for lang, count in sorted_stats:
        print(f"{lang:<20} | {count:<15,}")
    print("-" * 38)
    print(f"{'TOTAL':<20} | {total_loc_overall:<15,}")
    print(f"\nTotal source files processed: {total_files_processed}")
    print("--- End of Report ---\n")

# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(
        description="Analyzes a directory structure and reports line-of-code (LOC) statistics per programming language.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "target_directory",
        nargs="?",
        help="The target directory to analyze. If not provided, the user will be prompted."
    )
    parser.add_argument(
        "--ignore-dirs",
        nargs="+",
        default=[],
        help="Additional directory names to ignore (e.g., 'my_build_dir' 'temp_data').\n"
             f"Defaults: {', '.join(DEFAULT_IGNORE_DIRS)}"
    )
    parser.add_argument(
        "--ignore-files",
        nargs="+",
        default=[],
        help="Additional exact file names to ignore (e.g., 'config.ini' 'test_data.json').\n"
             f"Defaults: {', '.join(DEFAULT_IGNORE_FILES)}"
    )
    parser.add_argument(
        "--ignore-exts",
        nargs="+",
        default=[],
        help="Additional file extensions to ignore (e.g., '.xml' '.md').\n"
             f"Defaults: {', '.join(DEFAULT_IGNORE_EXTENSIONS)}"
    )

    args = parser.parse_args()

    target_dir = args.target_directory
    if not target_dir:
        target_dir = input("Enter the target directory path to analyze: ").strip()

    if not os.path.isdir(target_dir):
        print(f"Error: The specified path '{target_dir}' is not a valid directory or does not exist.")
        return

    # Combine default and user-provided ignores
    current_ignore_dirs = DEFAULT_IGNORE_DIRS.union(set(d.lower() for d in args.ignore_dirs))
    current_ignore_files = DEFAULT_IGNORE_FILES.union(set(args.ignore_files))
    current_ignore_extensions = DEFAULT_IGNORE_EXTENSIONS.union(set(args.ignore_exts))

    print("\n--- Configuration ---")
    print(f"Target Directory: {os.path.abspath(target_dir)}")
    print(f"Ignoring Directories: {', '.join(sorted(list(current_ignore_dirs)))}")
    print(f"Ignoring Files: {', '.join(sorted(list(current_ignore_files)))}")
    print(f"Ignoring Extensions: {', '.join(sorted(list(current_ignore_extensions)))}")
    print("Recognized Languages & Comment Prefixes:")
    for ext, (lang, prefix) in LANGUAGE_DEFINITIONS.items():
        print(f"  {ext}: {lang} (Comment: '{prefix if prefix else 'N/A'}')")
    print("---------------------\n")


    loc_stats, files_processed, total_loc = analyze_directory(
        target_dir,
        current_ignore_dirs,
        current_ignore_files,
        current_ignore_extensions
    )
    print_report(loc_stats, files_processed, total_loc)

if __name__ == "__main__":
    main()