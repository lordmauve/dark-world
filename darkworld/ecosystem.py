"""The ecosystem of plants and things."""
import asyncio
import random

from .world import Collision
from .actor import Pickable
from .items import Shroom
from . import client


def tick():
    shroom = Pickable(Shroom)
    while True:
        pos = random.choice(client.light_world.foliage_area)
        try:
            client.light_world.spawn(shroom, pos=pos)
        except Collision:
            continue
        else:
            print(f'Spawned shroom at {shroom.pos}')
            break


async def run_ecosystem():
    try:
        while True:
            if client.Client.clients:
                tick()
            await asyncio.sleep(30)
    except asyncio.CancelledError:
        return


task = None


def start_processes():
    global task
    task = asyncio.ensure_future(run_ecosystem())


def stop_processes():
    if task:
        task.cancel()
