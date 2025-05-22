import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path
import re
from datetime import datetime

class DirectoryCreatorGUI:
    def __init__(self, master):
        self.master = master
        master.title("Directory Structure Creator")
        master.geometry("900x700")
        master.configure(bg="#ffffff")  # Set background color to white
        master.resizable(False, False)

        # Set default base directory (update this to your desired default)
        self.default_base_dir = os.path.expanduser("~")  # User's home directory

        # Title Label
        self.title_label = tk.Label(master, text="Directory Structure Creator", font=("Helvetica", 18, "bold"), bg="#ffffff")
        self.title_label.pack(pady=10)

        # Instructions Label
        instructions = (
            "Paste your directory structure below.\n"
            "Ensure that indentation is consistent (use spaces or tabs).\n"
            "Example:\n"
            "project_manager_mvp/\n"
            "├── core.py\n"
            "├── plugins/\n"
            "│   ├── __init__.py\n"
            "│   └── gui_plugin.py\n"
            "..."
        )
        self.instructions_label = tk.Label(master, text=instructions, justify='left', bg="#ffffff", font=("Helvetica", 10))
        self.instructions_label.pack(padx=10, anchor='w')

        # Text area for directory structure
        self.text_area = scrolledtext.ScrolledText(master, width=110, height=20, font=("Courier", 10), bg="#f9f9f9", fg="#000000", borderwidth=1, relief="solid")
        self.text_area.pack(padx=10, pady=(5, 15))

        # Base directory selector frame
        self.base_dir_frame = tk.Frame(master, bg="#ffffff")
        self.base_dir_frame.pack(padx=10, fill='x')

        self.base_dir_label = tk.Label(self.base_dir_frame, text="Base Directory:", font=("Helvetica", 12), bg="#ffffff")
        self.base_dir_label.pack(side='left', pady=5)

        self.base_dir_var = tk.StringVar()
        self.base_dir_var.set(self.default_base_dir)

        self.base_dir_entry = tk.Entry(self.base_dir_frame, textvariable=self.base_dir_var, width=80, font=("Helvetica", 12), bg="#f9f9f9", fg="#000000", borderwidth=1, relief="solid")
        self.base_dir_entry.pack(side='left', padx=(10, 5), pady=5)

        self.browse_button = tk.Button(self.base_dir_frame, text="Browse", command=self.browse_directory, bg="#4CAF50", fg="white", font=("Helvetica", 12, "bold"), activebackground="#45a049", cursor="hand2")
        self.browse_button.pack(side='left', pady=5)

        # Create button
        self.create_button = tk.Button(master, text="Create Structure", command=self.create_structure, bg="#008CBA", fg="white", font=("Helvetica", 14, "bold"), activebackground="#007bb5", cursor="hand2")
        self.create_button.pack(pady=(0, 15))

        # Status log label
        self.status_label = tk.Label(master, text="Status Log:", font=("Helvetica", 14, "bold"), bg="#ffffff")
        self.status_label.pack(padx=10, anchor='w')

        # Status log area
        self.status_log = scrolledtext.ScrolledText(master, width=110, height=15, font=("Courier", 10), bg="#f9f9f9", fg="#000000", state='disabled', borderwidth=1, relief="solid")
        self.status_log.pack(padx=10, pady=(5, 10))

    def browse_directory(self):
        selected_dir = filedialog.askdirectory(initialdir=self.default_base_dir, title="Select Base Directory")
        if selected_dir:
            self.base_dir_var.set(selected_dir)

    def log_status(self, message):
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
        self.status_log.config(state='normal')
        self.status_log.insert(tk.END, timestamp + message + "\n")
        self.status_log.see(tk.END)
        self.status_log.config(state='disabled')
        self.master.update_idletasks()

    def parse_structure(self, structure_text):
        lines = structure_text.splitlines()
        if not lines:
            raise ValueError("The directory structure is empty.")

        stack = []  # Stack to keep track of current path based on levels
        base_path = Path(self.base_dir_var.get())

        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue  # Skip empty lines

            # Replace tree-drawing characters with spaces
            line_processed = re.sub(r'[│├└─]+', ' ', line)
            # Determine the level based on the number of leading spaces
            leading_spaces = len(line) - len(line.lstrip(' '))
            level = leading_spaces // 4  # Adjust if your indentation is different

            name = line_processed.strip()

            if not name:
                raise ValueError(f"Invalid line at {line_number}: '{line}'")

            is_dir = name.endswith('/')
            name = name.rstrip('/')

            # Adjust the stack to the current level
            if level > len(stack):
                raise ValueError(f"Inconsistent indentation at line {line_number}: '{line}'")
            elif level < len(stack):
                stack = stack[:level]

            # Current path
            current_path = base_path.joinpath(*stack, name)

            if is_dir:
                stack.append(name)

            yield (current_path, is_dir, line_number)

    def create_structure(self):
        structure_text = self.text_area.get("1.0", tk.END).strip()
        base_dir = self.base_dir_var.get().strip()

        # Clear previous status log
        self.status_log.config(state='normal')
        self.status_log.delete('1.0', tk.END)
        self.status_log.config(state='disabled')

        if not structure_text:
            messagebox.showerror("Input Error", "Please paste the directory structure.")
            return

        if not base_dir:
            messagebox.showerror("Input Error", "Please specify a base directory.")
            return

        base_path = Path(base_dir)
        if not base_path.exists():
            try:
                base_path.mkdir(parents=True, exist_ok=True)
                self.log_status(f"Created base directory: {base_path}")
            except Exception as e:
                messagebox.showerror("Directory Error", f"Failed to create base directory: {e}")
                return
        else:
            self.log_status(f"Using existing base directory: {base_path}")

        try:
            for current_path, is_dir, line_number in self.parse_structure(structure_text):
                if is_dir:
                    if not current_path.exists():
                        current_path.mkdir(parents=True, exist_ok=True)
                        self.log_status(f"Created directory: {current_path}")
                    else:
                        self.log_status(f"Directory already exists: {current_path}")
                else:
                    if not current_path.exists():
                        current_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent directories exist
                        current_path.touch()
                        self.log_status(f"Created file: {current_path}")
                    else:
                        self.log_status(f"File already exists: {current_path}")

            messagebox.showinfo("Success", "Directory structure created successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            self.log_status(f"Error: {e}")

def main():
    root = tk.Tk()
    gui = DirectoryCreatorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()