import asyncio

import aiohttp
from aiohttp import web
from .client import Client

from .ecosystem import start_processes, stop_processes
from .persistence import init_world, save_world


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
    for c in list(Client.clients.values()):
        ws = c.ws
        await ws.close(
            code=aiohttp.WSCloseCode.GOING_AWAY,
            message='Server shutdown'
        )
    stop_processes()
    save_world()

app.on_shutdown.append(on_shutdown)

loop = asyncio.get_event_loop()


def run_server(*, port=8000):
    """Run the server."""
    init_world()
    start_processes()
    web.run_app(app, port=port)
