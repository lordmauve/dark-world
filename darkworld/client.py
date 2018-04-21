import inspect
import traceback
import json
import asyncio
import weakref
import re

from .coords import Rect, Direction, DIRECTION_MAP
from .world import Collision
from .actor import PC
from .items import Inventory
from .dialog import InventoryDialog
from .persistence import pickle_atomic, load_pickle


loop = asyncio.get_event_loop()

# The world into which clients spawn
light_world = None


class ClientSight:
    """Base class for subscribing to world events."""
    def __init__(self, actor):
        self.client = actor.client
        self.actor = actor
        self.world = None
        self.restart()

    def __repr__(self):
        return f'<ClientSight for {self.client.name} in {self.world}>'

    def stop(self):
        if self.world:
            self.world.unsubscribe(self)
        self.world = None

    def restart(self):
        self.stop()
        self.world = self.actor.world
        self._update_rect()
        self.world.subscribe(self)

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
    clients = weakref.WeakValueDictionary()

    @classmethod
    def broadcast(cls, msg):
        encoded = json.dumps(msg)
        for v in cls.clients.values():
            v._write(encoded)

    def __init__(self, ws):
        self.name = None
        self.outqueue = asyncio.Queue()
        self.ws = ws
        self._gold = 0  # TODO: load from storage
        self.actor = None
        self.dialog = None
        self.caps = set()

    def can(self, capability):
        """Return True if the player has a capability."""
        return capability in self.caps

    def grant(self, capability):
        """Grant a capability to the player."""
        self.caps.add(capability)

    @property
    def gold(self):
        """Return the amount of gold."""
        return self._gold

    @gold.setter
    def gold(self, v):
        """Set the amount of gold."""
        self._gold = v
        self.write({
            'op': 'setvalue',
            'gold': self._gold
        })

    def write(self, msg):
        """Write a message to the client."""
        self._write(json.dumps(msg))

    def _write(self, msg):
        self.outqueue.put_nowait(msg)

    def close(self):
        if not self.name:
            return
        print(f"{self.name} disconnected")
        self.outqueue.put_nowait(None)
        Client.broadcast({
            'op': 'announce',
            'msg': f"{self.name} disconnected"
        })
        self.clients.pop(self.name, None)
        if self.actor:
            self.actor.kill(effect='disconnect')

    def save(self):
        pickle_atomic(self.caps_file, self.caps)
        pickle_atomic(self.inventory_file, self.inventory)

    @classmethod
    def save_all(cls):
        """Save all connected clients."""
        for c in cls.clients.values():
            c.save()

    def handle_west(self):
        if self.actor.alive:
            self.actor.move_step(Direction.WEST)

    def handle_east(self):
        if self.actor.alive:
            self.actor.move_step(Direction.EAST)

    def handle_north(self):
        if self.actor.alive:
            self.actor.move_step(Direction.NORTH)

    def handle_south(self):
        if self.actor.alive:
            self.actor.move_step(Direction.SOUTH)

    @property
    def inventory_file(self):
        return f'{self.name}-inventory.pck'

    @property
    def caps_file(self):
        return f'{self.name}-caps.pck'

    @property
    def data_file(self):
        return f'{self.name}-data.pck'

    def handle_auth(self, name):
        if not re.match(r'^[a-z][a-z_0-9]*[a-z]$', name, flags=re.I):
            return self.write({
                'op': 'authfail',
                'reason': 'Invalid name; please use only lowercase letters ' +
                          'and numbers'
            })

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
        self.inventory = load_pickle(self.inventory_file) or Inventory()
        self.caps = load_pickle(self.caps_file) or set()
        self.respawn()

    def text_message(self, msg):
        """Send a text message to the user."""
        self.write({
            'op': 'announce',
            'msg': msg
        })

    def respawn(self, msg=None):
        self.spawn_actor()
        self.handle_refresh()
        if msg:
            self.text_message(msg)

    def spawn_actor(self):
        self.actor = PC(self)

        # FIXME: need better way of finding good spawn points
        dirs = list(DIRECTION_MAP.values())
        for d in dirs:
            try:
                self.actor.spawn(light_world, pos=d)
            except Collision:
                continue
            else:
                break
        else:
            self.actor.spawn(light_world)
        self.sight = ClientSight(self.actor)

    def handle_say(self, msg):
        actor = self.actor
        for obj in actor.world.query(actor.pos, actor.sight):
            # FIXME: should really be sight range of other actor
            if isinstance(obj, PC):
                obj.client.say(self.name, msg)

    def say(self, sender, msg):
        """Say a message."""
        self.write({
            'op': 'say',
            'user': sender,
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
            'objs': objs,
            'gold': self.gold,
            'health': self.actor.health,
        })

    def handle_act(self):
        if not self.actor.alive:
            return
        obj = self.actor.get_facing()
        if obj and not obj.standable:
            obj.on_act(self.actor)
        else:
            self.actor.attack()

    def handle_inventory(self):
        self.dialog = InventoryDialog(self.inventory)
        self.write({
            'op': 'dialog',
            **self.dialog.to_json(),
        })

    def handle_dlgresponse(self, value):
        if not self.actor.alive:
            return
        if not self.dialog:
            return
        self.dialog.on_response(self, value)

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
                    continue
                if op != 'dlgresponse' and self.dialog:
                    self.dialog = None
                    self.write({'op': 'canceldialog'})
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
