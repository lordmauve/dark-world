import random
from .actor import Enemy


ENEMIES = [
    'enemies/bat',
    'enemies/spider',
    'enemies/rat',
]


def random_enemy():
    """Generate a random enemy."""
    return Enemy(random.choice(ENEMIES), 10)
