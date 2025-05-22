from components.theme import Theme
from components.board import Board
from components.cards import Card, Deck
from components.mechanics import MovementMechanic
from components.interactions import Interaction
from components.objectives import Objective
from utils.randomizer import weighted_choice, seed_randomizer
from utils.validator import validate_game_components
import json

class BoardGameGenerator:
    def __init__(self, config):
        self.config = config
        seed_randomizer(config.get('seed'))
        self.themes = Theme.load_themes(config['data_paths']['themes'])
        self.boards = Board.load_boards(config['data_paths']['boards'])
        self.cards = Card.load_cards(config['data_paths']['cards'])
        self.mechanics = MovementMechanic.load_mechanics(config['data_paths']['mechanics'])
        self.interactions = Interaction.load_interactions(config['data_paths']['interactions'])
        self.objectives = Objective.load_objectives(config['data_paths']['objectives'])

    def generate_theme(self):
        # Weighted choice can be implemented based on theme popularity or other factors
        return random.choice(self.themes)

    def generate_board(self, theme):
        # Filter boards based on theme compatibility
        compatible_boards = [board for board in self.boards if theme.name in board.zones]
        return random.choice(compatible_boards) if compatible_boards else random.choice(self.boards)

    def generate_mechanics(self):
        # Select multiple mechanics based on complexity settings
        selected_mechanics = random.sample(self.mechanics, k=2)  # Example: Select 2 mechanics
        return selected_mechanics

    def generate_interactions(self):
        # Choose interaction types
        return random.choice(self.interactions)

    def generate_objectives(self):
        # Select primary and secondary objectives
        primary = random.choice(self.objectives)
        secondary = random.sample([obj for obj in self.objectives if obj != primary], k=1)
        return {'primary': primary, 'secondary': secondary}

    def generate_cards(self):
        # Create different decks
        action_deck = Deck(self.cards, 'Action')
        event_deck = Deck(self.cards, 'Event')
        resource_deck = Deck(self.cards, 'Resource')
        challenge_deck = Deck(self.cards, 'Challenge')
        return {
            'Action': action_deck,
            'Event': event_deck,
            'Resource': resource_deck,
            'Challenge': challenge_deck
        }

    def assemble_game(self):
        theme = self.generate_theme()
        board = self.generate_board(theme)
        mechanics = self.generate_mechanics()
        interactions = self.generate_interactions()
        objectives = self.generate_objectives()
        cards = self.generate_cards()

        # Validate components
        errors = validate_game_components(theme, board, mechanics, interactions, objectives)
        if errors:
            raise ValueError(f"Game generation failed with errors: {errors}")

        game = {
            'Theme': {
                'Name': theme.name,
                'Description': theme.description,
                'Aesthetic Style': theme.aesthetic_style
            },
            'Board': {
                'Layout': board.layout,
                'Zones': board.zones,
                'Size': board.size,
                'Dynamic': board.dynamic
            },
            'Movement Mechanics': [
                {
                    'Name': mech.name,
                    'Description': mech.description,
                    'Parameters': mech.parameters
                } for mech in mechanics
            ],
            'Player Interactions': {
                'Type': interactions.type,
                'Description': interactions.description
            },
            'Objectives': {
                'Primary': {
                    'Description': objectives['primary'].description,
                    'Condition': objectives['primary'].condition
                },
                'Secondary': [
                    {
                        'Description': sec_obj.description,
                        'Condition': sec_obj.condition
                    } for sec_obj in objectives['secondary']
                ]
            },
            'Cards': {
                'Action Deck': [card.name for card in cards['Action'].cards],
                'Event Deck': [card.name for card in cards['Event'].cards],
                'Resource Deck': [card.name for card in cards['Resource'].cards],
                'Challenge Deck': [card.name for card in cards['Challenge'].cards]
            }
        }

        return game

    def export_game(self, game, format_='json', output_path='generated_game'):
        if format_ == 'json':
            with open(f"{output_path}.json", 'w') as f:
                json.dump(game, f, indent=4)
        elif format_ == 'txt':
            with open(f"{output_path}.txt", 'w') as f:
                json.dump(game, f, indent=4)
        # Additional formats can be implemented
        else:
            raise ValueError("Unsupported export format.")
