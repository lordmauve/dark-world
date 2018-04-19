import random
from contextlib import contextmanager
from timeit import default_timer
from itertools import product

from PIL import Image

from .coords import Direction, adjacent, random_dir
from .world import World
from .actor import Enemy, Teleporter, Scenery, Standable, Trigger
from .ai import EnemyAI


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
        },
        # accessible_area=set(logical_grid),
    )

    # Entrance
    entrance = set(product((-1, 0, 1), (-1, 0, 1)))
    logical_grid.update(entrance)

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

    Teleporter(target=light_world).spawn(w, (0, 0))

    logical_grid.difference_update(entrance)
    enemy_pos = random.sample(list(logical_grid), len(logical_grid) // 20)

    enemies = []
    for pos in enemy_pos:
        logical_grid.discard(pos)
        e = Enemy('enemies/bat', 10)
        e.spawn(w, pos)
        enemies.append(e)

    w.ai = EnemyAI(enemies)
    w.subscribe(w.ai)
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


def load_heightmap(filename, size, threshold=45):
    """Load accessible regions from the given heightmap."""
    heightmap = Image.open(filename)
    heightmap = heightmap.resize(
        (2 * size + 1,) * 2,
    )

    area = set()
    for x in range(-size, size + 1):
        for y in range(-size, size + 1):
            p = (x + size, y + size)
            h = heightmap.getpixel(p)
            if h > threshold:
                area.add((x, y))

    return area


def reachable(area, pos):
    """Find the area reachable from a given set of coordinates."""
    reachable = {pos, }
    edge = {pos, }
    while edge:
        pos = edge.pop()
        for d in Direction:
            p = adjacent(pos, d)
            if p not in area:
                continue
            if p in reachable:
                continue
            reachable.add(p)
            edge.add(p)
    return reachable


def create_light_world():
    SIZE = 320

    world_area = reachable(
        area=load_heightmap('assets/heightmap.png', SIZE),
        pos=(0, 0)
    )
    light_world = World(
        size=SIZE,
        metadata={
            'title': 'The Light World',
            'title_color': 'black',
            'sun_color': 0xffffff,
            'sun_intensity': 1,
            'ambient_color': 0xffffff,
            'ambient_intensity': 0.2
        },
        accessible_area=world_area
    )

    plant_areas = load_heightmap('assets/heightmap.png', SIZE, 55) & world_area

    TELEPORTER_POS = [
        (2, -13),
        (2, -15),
        (1, -14),
        (3, -14),
    ]

    trigger_pos = (2, -14)
    trigger = Trigger('nature/stone_obelisk').spawn(light_world, trigger_pos)
    plant_areas.discard(trigger_pos)
    for p in TELEPORTER_POS:
        plant_areas.discard(p)
        Teleporter(trigger=trigger).spawn(light_world, p)

    # Insert a bat for testing
    # Enemy('enemies/bat', 10).spawn(light_world, (1, 1))

    def spawn_random(cls, num, choices):
        positions = random.sample(list(plant_areas), num)
        plant_areas.difference_update(positions)
        for pos in positions:
            cls(
                random.choice(choices),
            ).spawn(
                light_world,
                pos=pos,
                direction=random_dir()
            )

    spawn_random(Scenery, 200, TREES)
    spawn_random(Scenery, 1000, BUSHES)
    spawn_random(Standable, 2500, PLANTS)
    return light_world


light_world = create_light_world()
