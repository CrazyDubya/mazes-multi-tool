import os
from pathlib import Path


def create_directory_tree(root):
    """
    Creates the directory tree for the board_game_generator project.

    Args:
        root (Path): The root directory where the tree will be created.
    """

    # Define the directory structure
    directories = [
        root / "components",
        root / "data",
        root / "utils",
    ]

    # Define the files to be created (relative to root)
    files = [
        # Root level files
        root / "generator.py",
        root / "main.py",

        # Components files
        root / "components" / "theme.py",
        root / "components" / "board.py",
        root / "components" / "cards.py",
        root / "components" / "mechanics.py",
        root / "components" / "interactions.py",
        root / "components" / "objectives.py",

        # Data files
        root / "data" / "themes.json",
        root / "data" / "boards.json",
        root / "data" / "cards.json",
        root / "data" / "mechanics.json",
        root / "data" / "interactions.json",
        root / "data" / "objectives.json",

        # Utils files
        root / "utils" / "randomizer.py",
        root / "utils" / "validator.py",
    ]

    # Create directories
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {directory}")
        except Exception as e:
            print(f"Failed to create directory {directory}: {e}")

    # Create empty files
    for file_path in files:
        try:
            # Ensure the parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # Create the file if it doesn't exist
            file_path.touch(exist_ok=True)
            print(f"Created file: {file_path}")
        except Exception as e:
            print(f"Failed to create file {file_path}: {e}")


def main():
    # Define the root directory name
    root_dir_name = "board_game_generator"
    root = Path.cwd() / root_dir_name

    # Create the root directory
    try:
        root.mkdir(exist_ok=True)
        print(f"Created root directory: {root}")
    except Exception as e:
        print(f"Failed to create root directory {root}: {e}")
        return

    # Create the directory tree
    create_directory_tree(root)


if __name__ == "__main__":
    main()
