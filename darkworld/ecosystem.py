"""The ecosystem of plants and things."""
import asyncio
import random

from .world import Collision
from .actor import Pickable
from .items import Shroom
from . import client
from .persistence import save_world


def tick():
    shroom = Pickable(Shroom)
    while True:
        pos = random.choice(client.light_world.foliage_area)
        try:
            client.light_world.spawn(shroom, pos=pos)
        except Collision:
            continue
        else:
            break


async def run_ecosystem():
    try:
        while True:
            if client.Client.clients:
                tick()
            await asyncio.sleep(30)
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
