import random
from collections import Counter, namedtuple


ITEM_TYPES = {}


def item(cls):
    """Register an item to the item types dict."""
    ITEM_TYPES[cls.singular] = cls
    return cls


class Stackable(namedtuple('Stackable', 'singular plural model')):
    """A stackable item."""

    def get_model(self):
        return self.model

    @property
    def image(self):
        return self.model

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
    item = random.choice(COLLECTABLES)
    return Collectable(item)


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
        if isinstance(obj, str):
            obj = ITEM_TYPES[obj]
        self.objects[obj] += 1

    def __iter__(self):
        """Iterate over items in the inventory as (obj, count) pairs."""
        yield from self.objects.items()

    def have(self, obj, count=1):
        """Return True if a player has an object."""
        if isinstance(obj, str):
            obj = ITEM_TYPES[obj]

        if obj not in self.objects:
            return False
        return self.objects[obj] >= count

    def take(self, obj, count=1):
        """Take items from the inventory."""
        if isinstance(obj, str):
            obj = ITEM_TYPES[obj]

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


iron = Stackable('iron ingot', 'iron ingots', 'iron')


@item
class Shroom(Stackable):
    singular = model = 'mushroom'
    plural = 'mushrooms'
    image = 'mushroom'

    @staticmethod
    def get_model():
        return random.choice((
            'nature/mushroom_brownTall',
            'nature/mushroom_redTall',
            'nature/mushroom_brown',
            'nature/mushroom_red'
        ))

    def __eq__(self, ano):
        return isinstance(ano, Shroom)

    def __hash__(self):
        return 42

    @staticmethod
    def on_use(pc):
        pc.client.inventory.take('mushroom', 1)
        if pc.client.can('eat_shrooms'):
            pc.client.text_message("You eat a safe mushroom.")
            pc.add_health(5)
        else:
            pc.client.text_message("You eat a mushroom. You feel sick.")
            pc.hit(-5, effect='vomit')


@item
class Banana(Stackable):
    singular = 'banana'
    plural = 'bananas'
    image = model = 'banana'

    @classmethod
    def get_model(cls):
        return cls.model

    @staticmethod
    def on_use(pc):
        pc.client.inventory.take('banana', 1)
        pc.client.text_message("You eat a delicious banana.")
        pc.add_health(5)


@item
class Elixir(Stackable):
    singular = image = model = 'elixir'
    plural = 'elixirs'

    @classmethod
    def get_model(cls):
        return cls.model

    @staticmethod
    def on_use(pc):
        health_needed = pc.max_health - pc.health
        if health_needed <= 0:
            pc.client.text_message("Your health is full.")
        else:
            pc.client.inventory.take('elixir', 1)
            pc.client.text_message("You feel invigorated.")
            pc.add_health(health_needed)


@item
class Torch(Stackable):
    singular = 'torch'
    plural = 'torches'
    image = model = 'torch'

    @staticmethod
    def on_use(pc):
        if pc.light_on:
            pc.client.text_message("You are already using a torch.")
        else:
            pc.client.text_message("You light a torch.")
            pc.client.inventory.take('torch', 1)
            pc.set_light(True)


class DumbItem(Stackable):
    def get_model(cls):
        return cls.model

    @staticmethod
    def on_use(pc):
        pc.client.text_message("You can't do anything with that.")


@item
class Iron(Stackable):
    singular = 'iron ingot'
    plural = 'iron ingots'
    image = model = 'iron'


ITEM_TYPES['iron'] = Iron


@item
class Axe(Stackable):
    singular = image = model = 'axe'
    plural = 'axes'


COLLECTABLES = [
    Banana,
    Iron,
]
