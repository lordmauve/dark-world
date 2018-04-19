import random
from contextlib import contextmanager
from timeit import default_timer

from .coords import Direction, adjacent
from .world import World
from .actor import Enemy, Teleporter, Scenery, Standable

ALL_DIRECTIONS = list(Direction)


def random_dir():
    """Return a random direction."""
    return random.choice(ALL_DIRECTIONS)


def erode(grid):
    for pos in list(grid):
        for d in Direction:
            grid.add(adjacent(pos, d))


def stochastic_erode(grid, prob=0.1):
    for pos in list(grid):
        for d in Direction:
            if random.random() <= prob:
                grid.add(adjacent(pos, d))


def border(grid):
    border = set()
    for pos in grid:
        for d in Direction:
            p = adjacent(pos, d)
            if p not in grid:
                border.add(p)
    return border


@contextmanager
def timeit(msg):
    start = default_timer()
    yield
    end = default_timer()
    print(f'{msg}: {end - start:.2}s')


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
            'ambient_intensity': 0.1,
            'world_tex': 'dark_terrain',
        }
    )

    with timeit('walk'):
        logical_grid = {(0, 0)}
        for i in range(random.randint(3, 6)):
            pos = (0, 0)
            last_dir = None
            for step in range(random.randint(50, 100)):
                dir = last_dir
                while dir is last_dir:
                    dir = random_dir()
                pos = adjacent(pos, dir)
                logical_grid.add(pos)

#    with timeit('erode'):
#        erode(logical_grid)
    with timeit('stochastic'):
        stochastic_erode(logical_grid)
    with timeit('border'):
        for p in border(logical_grid):
            Scenery(
                random.choice((
                    'nature/plant_bushLarge',
                ))
            ).spawn(
                w,
                p,
                direction=random_dir()
            )

    logical_grid.discard((0, 0))
    Teleporter(target=light_world).spawn(w, (0, 0))

    enemy_pos = random.sample(list(logical_grid), len(logical_grid) // 20)

    for pos in enemy_pos:
        logical_grid.discard(pos)
        Enemy('enemies/bat', 10).spawn(w, pos)

    return w


BUSHES = [
    'nature/plant_bushDetailed',
    'nature/plant_bushSmall',
    'nature/plant_flatLarge',
    'nature/mushroom_brownTall',
    'nature/mushroom_redTall',
]


TREES = [
    'nature/palm_small',
    'nature/palmDetailed_small',
    'nature/palm_large',
    'nature/palmDetailed_large',
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
    'nature/mushroom_redGroup',
    'nature/mushroom_red',
    'nature/plant_flatSmall',
    'nature/plant_bush',
    'nature/plant_bushLarge',
]


def create_light_world():
    light_world = World(
        size=20,
        metadata={
            'title': 'The Light World',
            'title_color': 'black',
            'sun_color': 0xffffff,
            'sun_intensity': 1,
            'ambient_color': 0xffffff,
            'ambient_intensity': 0.2
        }
    )
    Teleporter().spawn(light_world, (2, -13))

    # Insert a bat for testing
    # Enemy('enemies/bat', 10).spawn(light_world, (1, 1))

    def spawn_random(cls, num, choices):
        for _ in range(num):
            cls(
                random.choice(choices),
            ).spawn(
                light_world,
                direction=random_dir()
            )

    spawn_random(Scenery, 20, TREES)
    spawn_random(Scenery, 50, BUSHES)
    spawn_random(Standable, 100, PLANTS)
    return light_world


light_world = create_light_world()