"""The ecosystem of plants and things."""
import asyncio
import random

from .coords import random_dir
from .world import Collision
from .actor import Mushroom, Tree, Bush, Plant
from . import client
from .persistence import save_world


def tick():
    spawn_foliage(Mushroom.random())
    # No way of clearing bushes or plants yet
    # spawn_foliage(Plant.random())
#    if random.random() < 0.3:
#        spawn_foliage(Bush.random())
    if random.random() < 0.05:
        spawn_foliage(Tree.random())


def spawn_foliage(actor):
    for _ in range(5):
        pos = random.choice(client.light_world.foliage_area)
        if pos in client.light_world.grid:
            continue
        try:
            actor.spawn(
                client.light_world,
                pos=pos,
                direction=random_dir(),
                effect='grow'
            )
        except Collision:
            continue
        else:
            #print(f'Spawned {type(actor).__name__} at {pos}')
            return


async def run_ecosystem():
    try:
        while True:
            if client.Client.clients:
                tick()
            await asyncio.sleep(15)
    except asyncio.CancelledError:
        return


tasks = []


async def autosave():
    """Save the whole world every 5 minutes."""
    try:
        while True:
            await asyncio.sleep(300)
            save_world()
            client.Client.save_all()
    except asyncio.CancelledError:
        return


def start_processes():
    tasks.extend([
        asyncio.ensure_future(run_ecosystem()),
        asyncio.ensure_future(autosave())
    ])


def stop_processes():
    for task in tasks:
        task.cancel()
