import os
from pathlib import Path
import re


def parse_line(line):
    # Remove tree-drawing characters and strip whitespace
    clean_line = re.sub(r'[├└│─]+', '', line).strip()
    # Calculate the indentation level
    indent = len(line) - len(line.lstrip())
    is_dir = clean_line.endswith('/')
    name = clean_line.rstrip('/')
    return indent, name, is_dir


def create_structure_recursive(lines, base_path, indent_stack=[0]):
    while lines:
        line = lines[0]
        indent, name, is_dir = parse_line(line)

        # Handle indentation
        while indent < indent_stack[-1]:
            indent_stack.pop()

        if indent > indent_stack[-1]:
            indent_stack.append(indent)

        current_path = base_path / name

        if is_dir:
            print(f"Creating directory: {current_path}")
            current_path.mkdir(parents=True, exist_ok=True)
            lines = lines[1:]
            lines = create_structure_recursive(lines, current_path, indent_stack)
        else:
            print(f"Creating file: {current_path}")
            current_path.touch()
            lines = lines[1:]

    return lines


def create_structure(structure_text, base_dir):
    base_path = Path(base_dir)
    lines = structure_text.split('\n')
    create_structure_recursive(lines, base_path)
    print("Directory structure created successfully!")


def main():
    print("Welcome to the Recursive Directory Structure Creator")
    print("Paste your directory structure below. Press Enter twice when you're done:")

    structure_lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        structure_lines.append(line)

    structure_text = "\n".join(structure_lines)

    default_base_dir = os.path.expanduser("~")  # User's home directory
    base_dir = input(f"Enter the base directory (press Enter for default: {default_base_dir}): ").strip()
    if not base_dir:
        base_dir = default_base_dir

    create_structure(structure_text, base_dir)


if __name__ == "__main__":
    main()