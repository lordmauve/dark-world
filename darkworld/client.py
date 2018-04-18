import inspect
import traceback
import json
import asyncio

from .coords import Rect, Direction
from .world_gen import light_world
from .actor import PC


class ClientSight:
    """Base class for subscribing to world events."""
    def __init__(self, actor):
        self.client = actor.client
        self.actor = actor
        self._update_rect()
        self.actor.world.subscribe(self)

    def stop(self):
        self.actor.world.unsubscribe(self)

    def restart(self):
        self._update_rect()
        self.actor.world.subscribe(self)

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
        self.sight = ClientSight(self.actor)

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
