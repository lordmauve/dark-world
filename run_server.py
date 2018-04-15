"""Server for The Dark World game."""
import sys

if sys.version_info < (3, 6):
    sys.exit("The Dark World requires Python 3.6.")


import json
import traceback
import inspect
import asyncio

import asyncio_redis
import websockets

# IP Address of Redis storage
REDIS = ('172.17.0.2', 6379)


class Client:
    clients = {}

    @classmethod
    def broadcast(cls, msg):
        encoded = json.dumps(msg)
        for v in cls.clients.values():
            v._write(encoded)

    def __init__(self, ws):
        self.name = None
        self.outqueue = asyncio.Queue()
        self.ws = ws

    def write(self, msg):
        """Write a message to the client."""
        self._write(json.dumps(msg))

    def _write(self, msg):
        self.outqueue.put_nowait(msg)

    def close(self):
        print(f"{self.name} disconnected")
        self.outqueue.put_nowait(None)
        Client.broadcast({
            'op': 'announce',
            'msg': f"{self.name} disconnected"
        })
        self.clients.pop(self.name, None)

    def handle_auth(self, name):
        #TODO: validate name
        if self.name:
            return self.write({
                'op': 'authfail',
                'reason': 'You are already authenticated'
            })
        if name in self.clients:
            return self.write({
                'op': 'authfail',
                'reason': 'This name is already taken'
            })
        else:
            self.name = name
            self.clients[name] = self
            print(f"{name} connected")
            Client.broadcast({
                'op': 'announce',
                'msg': f"{name} connected"
            })
            return self.write({'op': 'authok'})

    async def sender(self):
        while True:
            msg = await self.outqueue.get()
            if not msg:
                break
            await self.ws.send(msg)

    async def receiver(self):
        try:
            async for js in self.ws:
                msg = json.loads(js)
                op = msg.pop('op')
                if not self.name and op != 'auth':
                    self.write({
                        'op': 'error',
                        'msg': 'You are not authenticated'
                    })
                try:
                    handler = getattr(self, f'handle_{op}')
                    if inspect.iscoroutinefunction(handler):
                        await handler(**msg)
                    else:
                        handler(**msg)
                except Exception as e:
                    traceback.print_exc()
                    self.write({
                        'op': 'error',
                        'msg': f'{type(e).__name__}: {e}',
                    })
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.close()


async def connect_redis(address, port=6379):
    global redis

    redis = await asyncio_redis.Connection.create(address, port=port)


async def connect(websocket, path):
    c = Client(websocket)
    loop.create_task(c.sender())
    await c.receiver()


loop = asyncio.get_event_loop()
loop.run_until_complete(connect_redis(*REDIS))
loop.run_until_complete(
    websockets.serve(connect, 'localhost', 5988)
)
loop.run_forever()
