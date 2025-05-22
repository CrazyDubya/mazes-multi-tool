import json
from generator import BoardGameGenerator


def main():
    # Load configuration
    with open('config.json', 'r') as f:
        config = json.load(f)

    # Initialize generator
    generator = BoardGameGenerator(config)

    # Assemble game
    game = generator.assemble_game()

    # Export game
    generator.export_game(game, format_='json', output_path='output/generated_game')

    print("Board game generated successfully! Check the output folder.")


if __name__ == "__main__":
    main()
