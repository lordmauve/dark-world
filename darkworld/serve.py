import asyncio
import tempfile
import pickle
from pathlib import Path

import aiohttp
from aiohttp import web
from .client import Client
from .world_gen import create_light_world
from . import client


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


savedir = Path.cwd() / 'savedata'
world_file = savedir / 'light_world.pck'


def init_world():
    if world_file.exists():
        with open(world_file, 'rb') as f:
            client.light_world = pickle.load(f)

        if client.light_world:
            print(f'World loaded from {world_file}')
            return
    client.light_world = create_light_world()


def save_world():
    tmpfile = tempfile.NamedTemporaryFile(dir=savedir, delete=False)
    try:
        pickle.dump(client.light_world, tmpfile, -1)
    except BaseException:
        Path(tmpfile.name).unlink()
        raise
    else:
        Path(tmpfile.name).rename(world_file)
        print(f'World state saved to {world_file}')


def run_server(*, port=8000):
    """Run the server."""
    if not savedir.exists():
        savedir.mkdir()
    init_world()
    web.run_app(app, port=port)
