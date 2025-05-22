# gui.py

import tkinter as tk
from tkinter import messagebox, filedialog
from checklist_engine import ChecklistEngine
from llm_interface import LLMInterface

class App:
    def __init__(self, root):
        self.root = root
        self.ce = ChecklistEngine()
        self.llm = LLMInterface()
        self.root.title("Project Manager MVP")
        self.create_widgets()

    def create_widgets(self):
        # Prompt Entry
        self.prompt_label = tk.Label(self.root, text="Enter prompt for new checklist:")
        self.prompt_label.pack(pady=5)
        self.prompt_entry = tk.Entry(self.root, width=50)
        self.prompt_entry.pack(pady=5)
        self.generate_button = tk.Button(self.root, text="Generate Checklist", command=self.generate_checklist)
        self.generate_button.pack(pady=5)

        # Checklist Selection
        self.checklist_label = tk.Label(self.root, text="Available Checklists:")
        self.checklist_label.pack(pady=5)
        self.checklist_listbox = tk.Listbox(self.root, width=50)
        self.update_checklist_list()
        self.checklist_listbox.pack(pady=5)
        self.load_button = tk.Button(self.root, text="Load Checklist", command=self.load_checklist)
        self.load_button.pack(pady=5)

        # Tasks Display
        self.tasks_frame = tk.Frame(self.root)
        self.tasks_frame.pack(pady=10)

    def update_checklist_list(self):
        self.checklist_listbox.delete(0, tk.END)
        for name in self.ce.list_checklists():
            self.checklist_listbox.insert(tk.END, name)

    def generate_checklist(self):
        prompt = self.prompt_entry.get()
        if prompt:
            checklist = self.llm.generate_checklist(prompt)
            name = f"checklist_{len(self.ce.list_checklists()) + 1}"
            self.ce.save_checklist(name, checklist)
            self.update_checklist_list()
            messagebox.showinfo("Success", f"Checklist '{name}' created.")
            self.prompt_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("Input Error", "Please enter a prompt.")

    def load_checklist(self):
        selection = self.checklist_listbox.curselection()
        if selection:
            name = self.checklist_listbox.get(selection[0])
            self.display_tasks(name)
        else:
            messagebox.showwarning("Selection Error", "Please select a checklist.")

    def display_tasks(self, name):
        for widget in self.tasks_frame.winfo_children():
            widget.destroy()
        checklist = self.ce.load_checklist(name)
        tk.Label(self.tasks_frame, text=f"Checklist: {name}", font=('Helvetica', 14, 'bold')).pack(pady=5)
        self.task_vars = []
        for idx, task in enumerate(checklist['tasks']):
            var = tk.BooleanVar(value=task['completed'])
            cb = tk.Checkbutton(self.tasks_frame, text=task['task'], variable=var,
                                command=lambda idx=idx, var=var: self.toggle_task(name, idx, var))
            cb.pack(anchor='w')
            self.task_vars.append(var)

    def toggle_task(self, name, idx, var):
        self.ce.update_task_status(name, idx, var.get())