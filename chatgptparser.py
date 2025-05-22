import os
import re
import sys


def find_section(markdown_text, section_title):
    """
    Finds the start and end indices of a section in the markdown text.
    Returns the content within the section.
    """
    # Escape regex special characters in section_title
    section_title_escaped = re.escape(section_title)
    # Match the header (### 1. Directory Structure)
    pattern = rf'^###\s+1\.\s+{section_title_escaped}\s*$'
    match = re.search(pattern, markdown_text, re.MULTILINE | re.IGNORECASE)
    if not match:
        return None

    # Find the start index
    start_index = match.end()
    # Find the next section header (### ...)
    next_header = re.search(r'^###\s+\d+\.\s+.+$', markdown_text[start_index:], re.MULTILINE)
    end_index = start_index + next_header.start() if next_header else len(markdown_text)

    # Extract the section content
    section_content = markdown_text[start_index:end_index]
    return section_content


def extract_code_block(section_content):
    """
    Extracts the first code block from the section content.
    Returns the code as a string.
    """
    code_block = re.search(r'```[\w]*\n([\s\S]*?)\n```', section_content)
    if not code_block:
        return None
    return code_block.group(1)


def parse_directory_structure(dir_structure_text):
    """
    Parses an ASCII directory tree and returns a list of file paths.
    """
    lines = dir_structure_text.strip().split('\n')
    base_path = ''
    current_dir = ''
    paths = []

    for line in lines:
        # Remove leading spaces and tree characters
        stripped_line = re.sub(r'^[├─└│\s]+', '', line).strip()
        if not stripped_line:
            continue  # Skip empty lines

        # Determine the indent level based on tree characters
        if re.match(r'^gpt-search-engine/$', stripped_line):
            base_path = stripped_line.rstrip('/')
            if not os.path.exists(base_path):
                os.makedirs(base_path)
                print(f"Created directory: {base_path}")
        elif re.match(r'^backend/$', stripped_line):
            current_dir = stripped_line.rstrip('/')
            full_dir_path = os.path.join(base_path, current_dir)
            if not os.path.exists(full_dir_path):
                os.makedirs(full_dir_path)
                print(f"Created directory: {full_dir_path}")
        elif re.match(r'^frontend/$', stripped_line):
            current_dir = stripped_line.rstrip('/')
            full_dir_path = os.path.join(base_path, current_dir)
            if not os.path.exists(full_dir_path):
                os.makedirs(full_dir_path)
                print(f"Created directory: {full_dir_path}")
        else:
            # Assume it's a file within the current directory
            file_name = stripped_line
            full_file_path = os.path.join(base_path, current_dir, file_name)
            paths.append(full_file_path)
            print(f"Identified file: {full_file_path}")

    return paths


def extract_file_contents(markdown_text):
    """
    Extracts file names and their corresponding code blocks from the markdown text.
    Returns a dictionary mapping file names to their code content.
    """
    # Find all file headers like ### 2. `server.js`
    file_headers = re.findall(r'^###\s+\d+\.\s+`([^`]+)`', markdown_text, re.MULTILINE)
    # Find all code blocks
    code_blocks = re.findall(r'```(?:javascript|json|html|css)?\n([\s\S]*?)\n```', markdown_text)

    # Ensure the number of file headers matches the number of code blocks
    if len(file_headers) != len(code_blocks):
        print(
            f"Warning: Number of file headers ({len(file_headers)}) and code blocks ({len(code_blocks)}) do not match.")

    file_contents = {}
    for header, code in zip(file_headers, code_blocks):
        file_contents[header] = code.strip()

    return file_contents


def create_files(file_paths, file_contents):
    """
    Creates files with the given paths and writes the corresponding contents.
    """
    for path in file_paths:
        file_name = os.path.basename(path)
        # Find the content for this file
        content = file_contents.get(file_name)
        if content:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Created file: {path}")
        else:
            print(f"No content found for file: {path}. Creating an empty file.")
            with open(path, 'w', encoding='utf-8') as f:
                pass  # Create an empty file


def main(markdown_file):
    if not os.path.isfile(markdown_file):
        print(f"Error: File '{markdown_file}' does not exist.")
        sys.exit(1)

    with open(markdown_file, 'r', encoding='utf-8') as f:
        markdown_text = f.read()

    # Extract Directory Structure section
    section_content = find_section(markdown_text, 'Directory Structure')
    if not section_content:
        print("Error: Directory Structure section not found.")
        sys.exit(1)

    # Extract the first code block in the Directory Structure section
    dir_structure_text = extract_code_block(section_content)
    if not dir_structure_text:
        print("Error: No code block found in Directory Structure section.")
        sys.exit(1)

    # Parse the directory structure to get file paths
    file_paths = parse_directory_structure(dir_structure_text)

    # Extract file contents from markdown
    file_contents = extract_file_contents(markdown_text)

    # Create files with contents
    create_files(file_paths, file_contents)

    print("All files have been created successfully.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python markdown_parser.py path_to_markdown_file.md")
        sys.exit(1)

    markdown_file = sys.argv[1]
    main(markdown_file)
