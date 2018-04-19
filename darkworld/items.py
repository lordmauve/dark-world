import random
from .actor import Collectable


# Items as (title, model)
COLLECTABLES = [
    ('Banana', 'banana'),
]


def generate_loot():
    """Generate a random piece of loot."""
    title, model = random.choice(COLLECTABLES)
    return Collectable(title, model)
