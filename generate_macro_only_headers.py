import os
import json
import re
from pathlib import Path

HEADER_FORMATS = (".h", ".hpp")
SOURCE_DIRS = ["../headers_generation/generated"]
OUTPUT_DIR = "macros_headers"

DEBUG = True

# TODO : Identify comments
def copy_directives(old_file, new_file):
    new_content = ""
    has_continuation = False
    comment = False
    comment_line = None
    with open(new_file, "w+") as new_f:
        with open(old_file) as f:
            try:
                for str_idx, line in enumerate(f):
                    content = line
                    # Check if this line has comment
                    # Firstly, check if there is whole comment in the line
                    if not comment: # TODO Are strip() calls needed here?
                        if content.strip().startswith("//"):
                            continue
                        content = re.sub(r"/\*(.*?)\*/", "", content)

                        if "/*" in content.strip():
                            comment = True
                            comment_line = str_idx
                            content = line[:content.find("/*")]

                    else:
                        if  "*/" in content.strip():
                            comment = False
                            content = line[content.find("*/") + 2:]
                            content = re.sub(r"/\*(.*?)\*/", "", content)
                            if "/*" in content.strip():
                                comment = True
                                comment_line = str_idx
                                content = line[:content.find("/*")]

                    # Write if it is directive
                    if has_continuation or content.strip().startswith("#"):
                        new_f.write(content)
                        if DEBUG:
                            print(content)

                    # Check if the next line should be processed
                    if content.strip().endswith("\\"):
                        has_continuation = True
                    else:
                        has_continuation = False
            except UnicodeDecodeError as ex:
                print("WARNING : Can't read file '{}'".format(old_file))
    if comment:
        print("WARNING : Comment till the EOF")

def copy_headers(search_dirs):
    search_files = {}
    duplicating = []

    # Copying tree without files, first

    for dir_path in search_dirs:
        dirname = os.path.basename(os.path.normpath(dir_path))
        for root, directories, files in os.walk(dir_path):
            for d in directories:
                path_in_dir = os.path.relpath(os.path.join(root, d), dir_path)
                rel_path = os.path.join(OUTPUT_DIR, dirname, path_in_dir)
                if not os.path.exists(rel_path):
                    if DEBUG:
                        print("Creating directory '{}'".format(rel_path))
                    os.makedirs(rel_path)

    # Processing headers

    for dir_path in search_dirs:
        dirname = os.path.basename(os.path.normpath(dir_path))
        for root, directories, files in os.walk(dir_path):
            for f in files:
                if not any(f.endswith(ext) for ext in HEADER_FORMATS):
                    continue
                file_path = os.path.join(root,f)
                path_in_dir = os.path.relpath(file_path, dir_path)
                new_file_path = os.path.join(OUTPUT_DIR, dirname, path_in_dir)
                if DEBUG:
                    print("Processing file '{}'".format(file_path))
                copy_directives(file_path, new_file_path)
                # print(file_path)

    

if __name__ == "__main__":
    copy_headers(SOURCE_DIRS)