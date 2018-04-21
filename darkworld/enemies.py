import random
from .actor import Enemy


ENEMIES = [
    ('enemies/bat', 10, 1),
    ('enemies/spider', 15, 2),
    ('enemies/rat', 30, 3),
]


def random_enemy():
    """Generate a random enemy."""
    enemy, health, damage = random.choice(ENEMIES)
    return Enemy(enemy, health, damage)
