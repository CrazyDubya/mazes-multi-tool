import random

def weighted_choice(choices):
    total = sum(weight for choice, weight in choices)
    r = random.uniform(0, total)
    upto = 0
    for choice, weight in choices:
        if upto + weight >= r:
            return choice
        upto += weight
    return choices[-1][0]

def seed_randomizer(seed=None):
    random.seed(seed)
