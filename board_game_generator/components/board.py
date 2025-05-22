import json

class Board:
    def __init__(self, layout, zones, size, dynamic=False):
        self.layout = layout
        self.zones = zones
        self.size = size
        self.dynamic = dynamic

    @staticmethod
    def load_boards(file_path):
        with open(file_path, 'r') as f:
            boards_data = json.load(f)
        boards = [Board(**board) for board in boards_data]
        return boards
