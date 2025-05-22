import json

class Theme:
    def __init__(self, name, description, aesthetic_style):
        self.name = name
        self.description = description
        self.aesthetic_style = aesthetic_style

    @staticmethod
    def load_themes(file_path):
        with open(file_path, 'r') as f:
            themes_data = json.load(f)
        themes = [Theme(**theme) for theme in themes_data]
        return themes
