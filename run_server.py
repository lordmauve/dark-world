"""Server for The Dark World game."""
import sys

if sys.version_info < (3, 6):
    sys.exit("The Dark World requires Python 3.6.")


import json
import traceback
import inspect
import asyncio
import random
import weakref
from enum import IntEnum
from collections import namedtuple

import asyncio_redis
import websockets

# IP Address of Redis storage
REDIS = ('172.17.0.2', 6379)


class Direction(IntEnum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3


class Rect(namedtuple('BaseRect', 'x1 x2 y1 y2')):
    """A rectangle of points within the world.

    End coordinates are inclusive.

    """
    @classmethod
    def from_center(cls, pos, radius):
        x, y = pos
        return cls(x - radius, x + radius, y - radius, y + radius)

    def coords(self):
        """Iterate over all cell coordinates in the range."""
        for x in range(self.x1, self.x2 + 1):
            for y in range(self.y1, self.y2 + 1):
                yield (x, y)

    def __contains__(self, pos):
        x, y = pos
        return (
            self.x1 <= x <= self.x2 and
            self.y1 <= y <= self.y2
        )


class Collision(Exception):
    """The operation would cause a collision."""


class World:
    """Represent a world grid.

    We allow subscribers to subscribe to see changes in the world.

    """
    def __init__(self, size):
        self.grid = {}
        self.by_name = {}
        self.subscriptions = weakref.WeakSet()
        self.size = size

    def spawn_point(self):
        """Return a random unoccupied spawn point in the world."""
        while True:
            x = random.randrange(0, self.size)
            y = random.randrange(0, self.size)
            if (x, y) not in self.grid:
                return x, y

    def get(self, pos, radius=3):
        objects = {}
        for x, y in Rect.from_center(pos, radius).coords():
            if not (0 <= x < self.size):
                continue
            if not (0 <= y < self.size):
                continue
            objects[x, y] = self.grid.get((x, y))
        return objects

    def spawn(self, obj, pos=None, effect=None):
        """Spawn an object into the grid."""
        if obj.name in self.by_name:
            raise Collision(
                f'{obj.name} is already in the world at {obj.pos}'
            )
        if not pos:
            pos = self.spawn_point()
        else:
            if pos in self.grid:
                raise Collision(
                    f'Position {pos} already contains {self.grid[pos].name}'
                )
        obj.pos = pos
        self.grid[pos] = obj
        self.by_name[obj.name] = obj
        self.get_subscribers(pos).spawn(obj, pos, effect)
        return pos

    def move(self, obj, to_pos):
        """Move the object in the grid."""
        if to_pos in grid:
            raise Collision(
                f'Target position {pos} is occupied by {self.grid[pos].name}'
            )
        from_pos = obj.pos
        obj.pos = to_pos
        self.get_subscribers(from_pos, to_pos).move(obj, from_pos, to_pos)

    def kill(self, obj, effect=None):
        """Remove an object from the grid."""
        pos = obj.pos
        del self.grid[pos]
        del self.by_name[obj.name]
        self.get_subscribers(pos).kill(obj, pos, effect)
        return pos

    def subscribe(self, subscriber):
        self.subscriptions.add(subscriber)

    def get_subscribers(self, *pos):
        """Iterate over subscribers to a point in the grid."""
        found = SubscriberSet()
        for s in self.subscriptions:
            if any(p in s.rect for p in pos):
                found.add(s)
        return found


class SubscriberSet(set):
    """A set of subscribers.

    This allows dispatching events to each subscriber.
    """
    def dispatcher(target):
        """Construct a method for dispatching to all subscribers in the set."""
        def method(self, *args):
            for subscriber in self:
                try:
                    getattr(subscriber, target)(*args)
                except Exception:
                    traceback.print_exc()
        method.__name__ = f'dispatch_{target}'
        return method

    move = dispatcher('moved')
    spawn = dispatcher('spawned')
    kill = dispatcher('killed')
    del dispatcher


class Subscriber:
    """Base class for subscribing to world events."""
    def __init__(self, rect, world):
        self.rect = rect

    def moved(self, obj, from_pos, to_pos):
        pass

    def spawned(self, obj, pos, effect):
        pass

    def killed(self, obj, pos, effect):
        pass


world = World(5)


class Actor:
    def __init__(self, name, world):
        self.name = name
        self.world = world
        self.world.spawn(self)

    def move(self, to_pos):
        """Move the actor in the world."""
        self.world.move(self, to_pos)

    def kill(self, effect=None):
        """Remove the actor from the world."""
        self.world.kill(self, effect)


class PC(Actor):
    def __init__(self, client):
        super().__init__(f'Player-{client.name}', world)
        self.client = client
        self.sight = 3
        self.direction = Direction.NORTH

    def to_json(self):
        return {
            'name': self.name,
            'model': 'advancedCharacter',
            'skin': 'adventurer',
            'pos': self.pos,
        }


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
        self.actor.kill(effect='disconnect')

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

        self.name = name
        self.clients[name] = self
        print(f"{name} connected")
        Client.broadcast({
            'op': 'announce',
            'msg': f"{name} connected"
        })
        self.write({'op': 'authok'})

        self.actor = PC(self)
        self.handle_refresh()

    def handle_refresh(self):
        center = self.actor.pos
        raw_objs = self.actor.world.get(center, self.actor.sight)
        objs = {}
        for pos, obj in objs.items():
            x, y = pos
            xy = x * 2 << 16 + y
            if obj is not None:
                obj = obj.to_json()
            objs[xy] = obj

        self.write({
            'op': 'refresh',
            'pos': center,
            'objs': objs
        })

    async def sender(self):
        while True:
            msg = await self.outqueue.get()
            if not msg:
                break
            await self.ws.send(msg)

    async def receiver(self):
        try:
            async for js in self.ws:
                # TODO: flood protection
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
