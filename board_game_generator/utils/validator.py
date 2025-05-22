def validate_game_components(theme, board, mechanics, interactions, objectives):
    errors = []
    if not theme:
        errors.append("Theme is missing.")
    if not board:
        errors.append("Board is missing.")
    if not mechanics:
        errors.append("Movement mechanics are missing.")
    if not interactions:
        errors.append("Player interactions are missing.")
    if not objectives:
        errors.append("Objectives are missing.")
    return errors
