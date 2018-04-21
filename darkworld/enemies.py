import random
from .actor import Enemy


ENEMIES = [
    ('enemies/bat', 10),
    ('enemies/spider', 15),
    ('enemies/rat', 20),
]


def random_enemy():
    """Generate a random enemy."""
    enemy, health = random.choice(ENEMIES)
    return Enemy(enemy, health)
