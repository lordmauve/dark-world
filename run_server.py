"""Server for The Dark World game."""
import sys

if sys.version_info < (3, 6):
    sys.exit("The Dark World requires Python 3.6.")


import json  # noqa
import traceback  # noqa
import inspect  # noqa
import asyncio  # noqa
import random  # noqa
import weakref  # noqa
from enum import IntEnum  # noqa
from collections import namedtuple  # noqa

import aiohttp  # noqa
from aiohttp import web  # noqa
# import asyncio_redis

# IP Address of Redis storage
REDIS = ('172.17.0.2', 6379)


class Direction(IntEnum):
    NORTH = 2
    EAST = 1
    SOUTH = 0
    WEST = 3


DIRECTION_MAP = {
    Direction.NORTH: (0, -1),
    Direction.SOUTH: (0, 1),
    Direction.WEST: (-1, 0),
    Direction.EAST: (1, 0),
}


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
    def __init__(self, size, metadata=None):
        self.grid = {}
        self.by_name = {}
        self.metadata = metadata or {}
        self.subscriptions = weakref.WeakSet()
        self.size = size

    def to_json(self):
        return self.metadata

    def spawn_point(self):
        """Return a random unoccupied spawn point in the world."""
        while True:
            x = random.randrange(0, self.size)
            y = random.randrange(0, self.size)
            if (x, y) not in self.grid:
                return x, y

    def query(self, pos, radius=3):
        """Iterate over objects in the world.

        `pos` may be a position, in which case `radius` tiles around it are
        considered, or a Rect, in which case `radius` is ignored.

        """
        if isinstance(pos, Rect):
            r = pos
        else:
            r = Rect.from_center(pos, radius)
        for x, y in r.coords():
            if not (0 <= x < self.size):
                continue
            if not (0 <= y < self.size):
                continue
            obj = self.grid.get((x, y))
            while obj:
                yield obj
                obj = obj.below

    def get(self, pos):
        """Get the object at the given coordinates."""
        return self.grid.get(pos)

    def spawn(self, obj, pos=None, effect=None):
        """Spawn an object into the grid."""
        if obj.name in self.by_name:
            raise Collision(
                f'{obj.name} is already in the world at {obj.pos}'
            )
        if not pos:
            pos = self.spawn_point()

        self._push(obj, pos)
        obj.pos = pos
        self.by_name[obj.name] = obj
        self.get_subscribers(pos).spawn(obj, pos, effect)
        return pos

    def _push(self, obj, pos):
        """Push an actor onto the actor stack at pos."""
        if pos not in self.grid:
            self.grid[pos] = obj
            obj.below = None
            return

        existing = self.grid[pos]

        if not existing.standable:
            raise Collision(
                f'Target position {pos} is occupied '
                f'by {existing.name}'
            )
        self.grid[pos] = obj
        obj.below = existing

    def _pop(self, pos):
        o = self.grid[pos]
        if o.below is not None:
            self.grid[pos] = o.below
        else:
            del self.grid[pos]

    def move(self, obj, to_pos):
        """Move the object in the grid."""
        from_pos = obj.pos
        below = obj.below
        if to_pos == from_pos:
            self.get_subscribers(from_pos).move(obj, from_pos, from_pos)
            return
        try:
            self._push(obj, to_pos)
        except Collision:
            # We still signal the move in order to update direction
            self.get_subscribers(from_pos).move(obj, from_pos, from_pos)
            raise
        else:
            if below is not None:
                self.grid[from_pos] = below
            else:
                del self.grid[from_pos]
            obj.pos = to_pos
            subs = self.get_subscribers(from_pos, to_pos)
            subs.move(obj, from_pos, to_pos)
            if below:
                below.on_exit(obj)
            if obj.below:
                obj.below.on_enter(obj)

    def notify_update(self, obj, effect=None):
        """Notify subscribers of an update to an object."""
        if obj.world is not self:
            return
        self.get_subscribers(obj.pos).update(obj, effect)

    def kill(self, obj, effect=None):
        """Remove an object from the grid."""
        pos = obj.pos
        self._pop(pos)
        del self.by_name[obj.name]
        self.get_subscribers(pos).kill(obj, pos, effect)
        return pos

    def subscribe(self, subscriber):
        self.subscriptions.add(subscriber)

    def unsubscribe(self, subscriber):
        self.subscriptions.discard(subscriber)

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
    update = dispatcher('updated')
    kill = dispatcher('killed')
    del dispatcher


class Subscriber:
    """Base class for subscribing to world events."""
    def __init__(self, rect, world):
        self.rect = rect

    def moved(self, obj, from_pos, to_pos):
        pass

    def update(self, obj, effect):
        pass

    def spawned(self, obj, pos, effect):
        pass

    def killed(self, obj, pos, effect):
        pass


light_world = World(
    size=10,
    metadata={
        'title': 'The Light World',
        'title_color': 'black',
        'sun_color': 0xffffff,
        'sun_intensity': 1,
        'ambient_color': 0xffffff,
        'ambient_intensity': 0.2
    }
)


def create_dark_world():
    """Create an instance of a dark world."""
    w = World(
        size=10,
        metadata={
            'title': 'The Dark World',
            'title_color': 'white',
            'sun_color': 0x2222ff,
            'sun_intensity': 0.2,
            'ambient_color': 0x0000ff,
            'ambient_intensity': 0.1
        }
    )
    Enemy('enemies/bat', 10).spawn(w, (2, 0))
    Teleporter(target=light_world).spawn(w, (0, 0))
    return w


def adjacent(pos, direction):
    """Get the adjacent map coordinates in a particular direction."""
    dx, dy = DIRECTION_MAP[direction]
    x, y = pos
    return x + dx, y + dy


class Actor:
    standable = False
    below = None

    def __init__(self, name):
        self.name = name
        self.below = None
        self.world = None
        self.pos = (0, 0)
        self.direction = Direction.NORTH

    def on_act(self, pc):
        """Called when the object is acted on by the PC."""

    def get_facing(self):
        """Get the object this actor is facing, if any."""
        facing_pos = adjacent(self.pos, self.direction)
        return self.world.get(facing_pos)

    def spawn(self, world, pos=None, direction=Direction.NORTH, effect=None):
        self.world = world
        self.direction = direction
        self.world.spawn(self, pos=pos, effect=effect)

    def attack(self):
        self.world.notify_update(self, 'attack')

    def move(self, to_pos):
        """Move the actor in the world."""
        self.world.move(self, to_pos)

    def move_step(self, direction):
        """Move by one step in the given direction."""
        self.direction = direction
        to_pos = adjacent(self.pos, self.direction)
        try:
            self.world.move(self, to_pos)
        except Collision:
            pass

    def kill(self, effect=None):
        """Remove the actor from the world."""
        self.world.kill(self, effect)


class PC(Actor):
    def __init__(self, client):
        super().__init__(f'Player-{client.name}')
        self.client = client
        self.sight = 8

    def to_json(self):
        return {
            'name': self.name,
            'model': 'advancedCharacter',
            'skin': 'adventurer',
            'pos': self.pos,
            'dir': self.direction.value
        }


class Enemy(Actor):
    next_uid = 0

    def __init__(self, model, health):
        self.model = model
        self.uid = self.next_uid
        type(self).next_uid += 1
        super().__init__(f'{model}-{self.uid}')

    def on_act(self, pc):
        from_dir = Direction((pc.direction.value + 2) % 4)
        print("Attacked from", from_dir)
        self.direction = from_dir
        self.move(self.pos)
        pc.attack()

    def to_json(self):
        return {
            'name': self.name,
            'model': self.model,
            'pos': self.pos,
            'dir': self.direction.value
        }


class Scenery(Actor):
    next_uid = 0
    scale = 16.0

    def __init__(self, model):
        self.model = model
        self.uid = self.next_uid
        type(self).next_uid += 1
        super().__init__(f'{model}-{self.uid}')

    def to_json(self):
        return {
            'name': self.name,
            'model': self.model,
            'scale': self.scale,
            'pos': self.pos,
            'dir': self.direction.value
        }


class Standable(Scenery):
    """Scenery you can stand on."""
    standable = True

    def on_enter(self, obj):
        """Subclasses should implement this to handle being stood on."""

    def on_exit(self, obj):
        """Subclasses should implement this to handle users exiting."""


class Teleporter(Standable):
    model = 'nature/campfireStones_rocks'
    scale = 10

    def __init__(self, target=None):
        self.target = target
        super().__init__(self.model)

    def on_enter(self, obj):
        if not isinstance(obj, PC):
            return
        obj.kill(effect='teleport')
        client = obj.client
        client.sight.destroy()
        target = self.target or create_dark_world()
        obj.world = target

        def respawn():
            client.sight = ActorSight(obj)
            obj.client.handle_refresh()
            try:
                obj.spawn(target, pos=(0, 0), effect='teleport')
            except Collision:
                obj.spawn(target, effect='teleport')
            print(f'{self.name} moved to {target}')
        loop.call_later(0.5, respawn)

    def on_exit(self, obj):
        print(f'{self.name} left by {obj.name}')


BUSHES = [
    'nature/plant_bushDetailed',
    'nature/plant_bushLarge',
    'nature/plant_bush',
    'nature/plant_bushSmall',
    'nature/plant_flatLarge',
    'nature/plant_flatSmall',
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
    'nature/mushroom_brownTall',
    'nature/mushroom_redGroup',
    'nature/mushroom_red',
    'nature/mushroom_redTall',
]

Teleporter().spawn(light_world, (0, 0))
Enemy('enemies/bat', 10).spawn(light_world, (1, 1))

for _ in range(10):
    Scenery(
        random.choice(BUSHES),
    ).spawn(
        light_world,
        direction=random.choice(list(Direction))
    )
    Standable(
        random.choice(PLANTS),
    ).spawn(
        light_world,
        direction=random.choice(list(Direction))
    )


class ActorSight:
    """Base class for subscribing to world events."""
    def __init__(self, actor):
        self.client = actor.client
        self.actor = actor
        self._update_rect()
        self.actor.world.subscribe(self)

    def destroy(self):
        self.actor.world.unsubscribe(self)

    def _update_rect(self):
        self.rect = Rect.from_center(self.actor.pos, self.actor.sight)

    def moved(self, obj, from_pos, to_pos):
        if obj is self.actor:
            could_see = set(self.actor.world.query(from_pos, self.actor.sight))
            self._update_rect()
            now_see = set(self.actor.world.query(to_pos, self.actor.sight))
            for newobj in now_see - could_see:
                self.spawned(newobj, newobj.pos, 'fade')
            self.client.write({
                'op': 'moved',
                'obj': obj.to_json(),
                'from_pos': from_pos,
                'to_pos': to_pos,
                'track': True
            })
            for lostobj in could_see - now_see:
                self.killed(lostobj, lostobj.pos, 'fade')
        else:
            self.client.write({
                'op': 'moved',
                'obj': obj.to_json(),
                'from_pos': from_pos,
                'to_pos': to_pos,
                'track': False
            })
            if to_pos not in self.rect:
                self.client.write({
                    'op': 'killed',
                    'obj': obj.to_json(),
                    'effect': 'fade',
                    'track': obj is self.actor
                })

    def updated(self, obj, effect):
        self.client.write({
            'op': 'update',
            'obj': obj.to_json(),
            'effect': effect
        })

    def spawned(self, obj, pos, effect):
        self.client.write({
            'op': 'spawned',
            'obj': obj.to_json(),
            'effect': effect,
            'track': obj is self.actor
        })

    def killed(self, obj, pos, effect):
        self.client.write({
            'op': 'killed',
            'obj': obj.to_json(),
            'effect': effect,
            'track': obj is self.actor
        })


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
        if self.actor:
            self.actor.kill(effect='disconnect')

    def handle_west(self):
        self.actor.move_step(Direction.WEST)

    def handle_east(self):
        self.actor.move_step(Direction.EAST)

    def handle_north(self):
        self.actor.move_step(Direction.NORTH)

    def handle_south(self):
        self.actor.move_step(Direction.SOUTH)

    def handle_auth(self, name):
        # TODO: validate name
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

        self.spawn_actor()
        self.handle_refresh()

    def spawn_actor(self):
        self.actor = PC(self)
        self.actor.spawn(light_world)
        self.sight = ActorSight(self.actor)

    def handle_say(self, msg):
        actor = self.actor
        for obj in actor.world.query(actor.pos, actor.sight):
            # FIXME: should really be sight range of other actor
            if isinstance(obj, PC):
                obj.client.write({
                    'op': 'say',
                    'user': self.name,
                    'msg': msg
                })

    def handle_refresh(self):
        center = self.actor.pos
        objs = []
        for obj in self.actor.world.query(center, self.actor.sight):
            objs.append(obj.to_json())
        self.write({
            'op': 'refresh',
            'world': self.actor.world.to_json(),
            'pos': center,
            'objs': objs
        })

    def handle_act(self):
        obj = self.actor.get_facing()
        if obj:
            obj.on_act(self.actor)

    async def sender(self):
        while True:
            msg = await self.outqueue.get()
            if not msg:
                break
            await self.ws.send_str(msg)

    async def receiver(self):
        try:
            async for m in self.ws:
                # TODO: flood protection
                msg = m.json()
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
        finally:
            self.close()


# async def connect_redis(address, port=6379):
#     global redis
#
#     redis = await asyncio_redis.Connection.create(address, port=port)


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
# loop.run_until_complete(connect_redis(*REDIS))
web.run_app(app, port=8000)
