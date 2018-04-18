import asyncio

import aiohttp
from aiohttp import web
from .client import Client


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

app.on_shutdown.append(on_shutdown)

loop = asyncio.get_event_loop()


def run_server(*, port=8000):
    """Run the server."""
    web.run_app(app, port=port)
