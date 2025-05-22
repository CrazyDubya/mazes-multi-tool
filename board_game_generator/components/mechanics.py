import json

class MovementMechanic:
    def __init__(self, name, description, parameters):
        self.name = name
        self.description = description
        self.parameters = parameters

    @staticmethod
    def load_mechanics(file_path):
        with open(file_path, 'r') as f:
            mechanics_data = json.load(f)
        mechanics = [MovementMechanic(**mechanic) for mechanic in mechanics_data]
        return mechanics
