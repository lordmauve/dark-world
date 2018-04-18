import random

from .coords import Direction
from .world import World
from .actor import Enemy, Teleporter, Scenery, Standable


def create_dark_world():
    """Create an instance of a dark world."""
    w = World(
        size=10,
        metadata={
            'title': 'The Dark World',
            'title_color': 'white',
            'sun_color': 0x2222ff,
            'sun_intensity': 0.2,
            'ambient_color': 0x0000ff,
            'ambient_intensity': 0.1
        }
    )
    Enemy('enemies/bat', 10).spawn(w, (2, 0))
    Teleporter(target=light_world).spawn(w, (0, 0))
    return w


BUSHES = [
    'nature/plant_bushDetailed',
    'nature/plant_bushLarge',
    'nature/plant_bush',
    'nature/plant_bushSmall',
    'nature/plant_flatLarge',
    'nature/plant_flatSmall',
]

PLANTS = [
    'nature/grass_dense',
    'nature/grass',
    'nature/flower_red1',
    'nature/flower_red2',
    'nature/flower_red3',
    'nature/flower_blue1',
    'nature/flower_blue2',
    'nature/flower_blue3',
    'nature/flower_beige1',
    'nature/flower_beige2',
    'nature/flower_beige3',
    'nature/mushroom_brownGroup',
    'nature/mushroom_brown',
    'nature/mushroom_brownTall',
    'nature/mushroom_redGroup',
    'nature/mushroom_red',
    'nature/mushroom_redTall',
]


def create_light_world():
    light_world = World(
        size=10,
        metadata={
            'title': 'The Light World',
            'title_color': 'black',
            'sun_color': 0xffffff,
            'sun_intensity': 1,
            'ambient_color': 0xffffff,
            'ambient_intensity': 0.2
        }
    )
    Teleporter().spawn(light_world, (0, 0))
    Enemy('enemies/bat', 10).spawn(light_world, (1, 1))

    for _ in range(10):
        Scenery(
            random.choice(BUSHES),
        ).spawn(
            light_world,
            direction=random.choice(list(Direction))
        )
        Standable(
            random.choice(PLANTS),
        ).spawn(
            light_world,
            direction=random.choice(list(Direction))
        )
    return light_world


light_world = create_light_world()
