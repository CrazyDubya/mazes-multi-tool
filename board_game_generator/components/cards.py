import json
import random

class Card:
    def __init__(self, card_type, name, effect):
        self.card_type = card_type
        self.name = name
        self.effect = effect

    @staticmethod
    def load_cards(file_path):
        with open(file_path, 'r') as f:
            cards_data = json.load(f)
        cards = [Card(**card) for card in cards_data]
        return cards

class Deck:
    def __init__(self, cards, deck_type):
        self.cards = [card for card in cards if card.card_type == deck_type]
        self.deck_type = deck_type
        self.shuffle_deck()

    def shuffle_deck(self):
        random.shuffle(self.cards)

    def draw_card(self):
        if not self.cards:
            self.shuffle_deck()
        return self.cards.pop() if self.cards else None
