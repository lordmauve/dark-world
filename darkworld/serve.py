import asyncio
import tempfile
import pickle
from pathlib import Path

import aiohttp
from aiohttp import web
from .client import Client
from .world_gen import create_light_world
from . import client

from .persistence import pickle_atomic, load_pickle


async def index(request):
    """Serve the index page."""
    with open('assets/index.html') as f:
        return web.Response(
            content_type='text/html',
            text=f.read()
        )


async def open_ws(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    c = Client(ws)
    loop.create_task(c.sender())
    await c.receiver()
    return web.Response()


app = web.Application()
app.add_routes([
    web.get('/', index),
    web.get('/ws', open_ws),
    web.static('/', 'assets'),
])


async def on_shutdown(app):
    for client in list(Client.clients.values()):
        ws = client.ws
        await ws.close(
            code=aiohttp.WSCloseCode.GOING_AWAY,
            message='Server shutdown'
        )
    save_world()

app.on_shutdown.append(on_shutdown)

loop = asyncio.get_event_loop()

world_file = 'light_world.pck'


def init_world():
    client.light_world = load_pickle(world_file)
    if client.light_world:
        print(f'World loaded from {world_file}')
    else:
        client.light_world = create_light_world()


def save_world():
    pickle_atomic(world_file, client.light_world)
    print(f'World state saved to {world_file}')


def run_server(*, port=8000):
    """Run the server."""
    init_world()
    web.run_app(app, port=port)
