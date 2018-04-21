import random
from .actor import Enemy


ENEMIES = [
    'enemies/bat',
    'enemies/spider'
]


def random_enemy():
    """Generate a random enemy."""
    return Enemy(random.choice(ENEMIES), 10)
