import random
from collections import Counter, namedtuple


# A stackable item
class Stackable(namedtuple('Stackable', 'singular plural model')):
    def on_use(self, pc):
        """Subclasses can implement this."""


class Unique(Stackable):
    """An item that does not stack."""
    def __eq__(self, ano):
        return ano is self

    def __hash__(self):
        return id(self)


def generate_loot():
    """Generate a random piece of loot."""
    from .actor import Collectable
    title, model = random.choice(COLLECTABLES)
    return Collectable(title, model)


class InsufficientItems(Exception):
    """There are not sufficient items of this type."""


class NoItems(InsufficientItems):
    """There are no items of this type."""


class Inventory:
    """A player's inventory."""

    def __init__(self, objects=[]):
        self.objects = Counter(objects)

    def add(self, obj, count=1):
        """Add an object to the inventory."""
        self.objects[obj] += 1

    def __iter__(self):
        """Iterate over items in the inventory as (obj, count) pairs."""
        yield from self.objects.items()

    def have(self, obj, count=1):
        """Return True if a player has an object."""
        if obj not in self.objects:
            return False
        return self.objects[obj] >= count

    def take(self, obj, count=1):
        """Take items from the inventory."""
        if obj not in self.objects:
            raise NoItems(f'You have no {obj.plural}')

        have = self.objects[obj]
        if have > count:
            self.objects[obj] -= count
        elif have == count:
            del self.objects[obj]
        elif have == 1:
            raise InsufficientItems(f'You only have {have} {obj.singular}')
        else:
            raise InsufficientItems(f'You only have {have} {obj.plural}')


# Define items here
banana = Stackable('banana', 'bananas', 'banana')


class Shroom(Stackable):
    image = 'mushroom'

    def __eq__(self, ano):
        return isinstance(ano, Shroom)

    def __hash__(self):
        return 42

    def on_use(self, pc):
        pc.client.text_message("You eat a mushroom.")
        pc.add_health(5)
        pc.client.inventory.take(self, 1)


SHROOMS = [
    Shroom('mushroom', 'mushrooms', model)
    for model in [
        'nature/mushroom_brownTall',
        'nature/mushroom_redTall',
        'nature/mushroom_brown',
        'nature/mushroom_red']
]
shroom = SHROOMS[0]

COLLECTABLES = [
    banana,
]
