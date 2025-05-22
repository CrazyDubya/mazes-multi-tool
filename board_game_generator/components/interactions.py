import json

class Interaction:
    def __init__(self, type_, description):
        self.type = type_
        self.description = description

    @staticmethod
    def load_interactions(file_path):
        with open(file_path, 'r') as f:
            interactions_data = json.load(f)
        interactions = [Interaction(**interaction) for interaction in interactions_data]
        return interactions
