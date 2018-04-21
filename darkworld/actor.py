"""Actors are objects that can exist in the world."""
import uuid
import asyncio
import weakref

from .coords import Direction, adjacent, Rect
from .world import Collision
from .items import InsufficientItems


class Actor:
    serialisable = True
    standable = False
    below = None
    size = (1, 1)

    def __init__(self):
        self.uid = f'{type(self).__name__}-{uuid.uuid4()}'
        self.below = None
        self._world = None
        self.pos = (0, 0)
        self.direction = Direction.NORTH
        self.alive = False

    def __repr__(self):
        return f'<{type(self).__name__} {self.uid}>'

    @property
    def world(self):
        """Return the world."""
        return self._world and self._world()

    @world.setter
    def world(self, w):
        """Set the world.

        We hold only weak references to the world in most Actor objects. Only
        PC objects hold strong references to the world. This allows the world
        to be deallocated as soon as all the PCs leave, which is valuable for
        memory usage.

        """
        self._world = weakref.ref(w)

    def __getstate__(self):
        d = self.__dict__.copy()
        d.pop('_world', None)
        return d

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
        self.alive = True
        return self

    def attack(self):
        self.world.notify_update(self, 'attack')

    def take_damage(self, effect='damage'):
        self.world.notify_update(self, effect)

    def move(self, to_pos):
        """Move the actor in the world."""
        self.world.move(self, to_pos)

    def face(self, actor):
        x, y = self.pos
        ax, ay = actor.pos
        was_direction = self.direction
        if ax < x:
            self.direction = Direction.WEST
        elif ax > x:
            self.direction = Direction.EAST
        elif ay < y:
            self.direction = Direction.NORTH
        elif ay > y:
            self.direction = Direction.SOUTH
        if self.direction != was_direction:
            self.world.move(self, self.pos)

    def move_step(self, direction):
        """Move by one step in the given direction."""
        if not self.world:
            return
        self.direction = direction
        to_pos = adjacent(self.pos, self.direction)
        try:
            self.world.move(self, to_pos)
        except Collision:
            pass

    def kill(self, effect=None):
        """Remove the actor from the world."""
        if self.world:
            self.world.kill(self, effect)
        self.alive = False


class Mob(Actor):
    health = max_health = 10

    def hit(self, dmg, effect='damage'):
        self.health -= dmg
        if self.health <= 0:
            self.take_damage('damage-crit' if effect == 'damage' else effect)
            self.kill()
            self.on_death()
        else:
            self.take_damage(effect)

    def add_health(self, v):
        self.health = min(self.max_health, self.health + v)

    def on_death(self):
        pass


class PC(Mob):
    serialisable = False
    health = max_health = 30

    def __init__(self, client):
        super().__init__()
        self.title = client.name
        self.client = client
        self.sight = 8

    @property
    def world(self):
        return self._world

    @world.setter
    def world(self, w):
        self._world = w

    def hit(self, dmg, effect='damage'):
        super().hit(dmg, effect)
        self.client.write({
            'op': 'setvalue',
            'health': self.health
        })

    def add_health(self, v):
        super().add_health(v)
        self.client.write({
            'op': 'setvalue',
            'health': self.health
        })

    def on_death(self):
        self.client.write({
            'op': 'setvalue',
            'health': 0
        })
        self.client.text_message('You are dead. Game over.')
        loop = asyncio.get_event_loop()
        loop.call_later(
            5.0,
            self.client.respawn,
            'Welcome back to the land of the living.'
        )

    def to_json(self):
        return {
            'title': self.title,
            'name': self.uid,
            'model': 'advancedCharacter',
            'skin': 'adventurer',
            'pos': self.pos,
            'dir': self.direction.value
        }


class NPC(Actor):
    title = 'NPC'
    skin = 'skin_robot'

    def to_json(self):
        return {
            'title': self.title,
            'name': self.uid,
            'model': 'advancedCharacter',
            'skin': self.skin,
            'pos': self.pos,
            'dir': self.direction.value
        }


class Enemy(Mob):

    def __init__(self, model, health):
        self.health = health
        self.model = model
        super().__init__()

    def on_act(self, pc):
        self.face(pc)
        pc.attack()
        dmg = 1  # TODO: Calculate damage to apply
        self.hit(dmg)

    def on_death(self):
        from .items import generate_loot
        loot = generate_loot()
        loot.spawn(self.world, self.pos, effect='drop')

    def to_json(self):
        return {
            'name': self.uid,
            'model': self.model,
            'pos': self.pos,
            'dir': self.direction.value,
            'title': f'{self.health} health',
        }


class Scenery(Actor):
    scale = 16.0

    def __init__(self, model):
        super().__init__()
        self.model = model

    def to_json(self):
        return {
            'name': self.uid,
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
    have_trigger = False

    def __init__(self, target=None, trigger=None):
        self.target = target
        if trigger:
            self.have_trigger = True
            trigger.add_teleporter(self)
        super().__init__(self.model)

    def on_enter(self, obj):
        if not isinstance(obj, PC):
            return
        if not self.have_trigger:
            obj.alive = False
            loop = asyncio.get_event_loop()
            loop.call_later(0.2, self.teleport)

    def _target(self):
        """Get the target world to teleport to."""
        if self.target:
            return self.target
        else:
            from .world_gen import create_dark_world
            return create_dark_world()

    def teleport(self, target=None, pos=(0, 0)):
        obj = self.world.get(self.pos)
        if not isinstance(obj, PC):
            return
        obj.kill(effect='teleport')
        client = obj.client
        target = target or self._target()

        def respawn():
            # FIXME: we need to identify spawn point before we restart sight
            obj.world = target
            obj.pos = pos
            client.sight.restart()
            obj.client.handle_refresh()
            try:
                obj.spawn(target, pos=pos, effect='teleport')
            except Collision:
                obj.spawn(target, effect='teleport')
        loop = asyncio.get_event_loop()
        loop.call_later(1.0, respawn)


class Trigger(Scenery):
    def __init__(self, model):
        super().__init__(model)
        self.teleporters = []

    def add_teleporter(self, t):
        self.teleporters.append(t)

    def on_act(self, pc):
        if not pc.client.can('teleport'):
            pc.client.text_message("It doesn't seem to work...")
            return

        to_teleport = []
        for t in self.teleporters:
            o = t.world.get(t.pos)
            if isinstance(o, PC):
                x, y = t.pos
                x -= self.pos[0]
                y -= self.pos[1]
                to_teleport.append((t, (x, y)))

        if not pc.client.can('developer'):
            try:
                pc.client.inventory.take('mushroom', 2)
            except InsufficientItems as e:
                pc.client.text_message(
                    f"{e.args[0]}. You don't have enough "
                    "mushrooms to teleport!"
                )
                return

        if to_teleport:
            from .world_gen import create_dark_world
            target = create_dark_world()
            for teleporter, pos in to_teleport:
                teleporter.teleport(target, pos)
        else:
            pc.text_message('Nothing happened.')


class Large(Scenery):
    scale = 40

    def __init__(self, model, size, scale=None):
        super().__init__(model)
        self.size = size
        if scale:
            self.scale = scale
        else:
            self.scale = type(self).scale

    def bounds(self):
        x, y = self.pos
        w, h = self.size
        return Rect(x, x + w - 1, y, y + h - 1)

    @property
    def center(self):
        x, y = self.pos
        w, h = self.size
        return x + (w - 1) / 2, y + (h - 1) / 2

    def to_json(self):
        j = super().to_json()
        j['pos'] = self.center
        return j


class Block(Scenery):
    scale = 16

    def __init__(self, model, scale):
        super().__init__(model)
        self.scale = type(self).scale * scale


class Pickable(Scenery):
    """An object that can be picked."""

    def __init__(self, item):
        self.item = item
        super().__init__(item.get_model())

    def on_act(self, pc):
        self.kill()
        pc.client.text_message(f'Picked a {self.item.singular}')
        pc.client.inventory.add(self.item)


class Collectable(Standable):
    """A collectable object."""
    scale = 1

    def __init__(self, item):
        self.item = item
        super().__init__(item.get_model())

    def on_enter(self, pc):
        self.kill()
        pc.client.text_message(f'Picked up a {self.item.singular}')
        pc.client.inventory.add(self.item)
