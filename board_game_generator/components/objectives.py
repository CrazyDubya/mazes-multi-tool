import json

class Objective:
    def __init__(self, description, condition):
        self.description = description
        self.condition = condition

    @staticmethod
    def load_objectives(file_path):
        with open(file_path, 'r') as f:
            objectives_data = json.load(f)
        objectives = [Objective(**obj) for obj in objectives_data]
        return objectives
