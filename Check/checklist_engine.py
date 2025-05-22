# checklist_engine.py

import json
import os

class ChecklistEngine:
    def __init__(self, checklist_dir='checklists'):
        self.checklist_dir = checklist_dir
        os.makedirs(self.checklist_dir, exist_ok=True)

    def load_checklist(self, name):
        path = os.path.join(self.checklist_dir, f'{name}.json')
        with open(path, 'r') as file:
            checklist = json.load(file)
        return checklist

    def save_checklist(self, name, checklist):
        path = os.path.join(self.checklist_dir, f'{name}.json')
        with open(path, 'w') as file:
            json.dump(checklist, file, indent=4)

    def list_checklists(self):
        files = os.listdir(self.checklist_dir)
        return [f[:-5] for f in files if f.endswith('.json')]

    def update_task_status(self, checklist_name, task_index, status):
        checklist = self.load_checklist(checklist_name)
        checklist['tasks'][task_index]['completed'] = status
        self.save_checklist(checklist_name, checklist)