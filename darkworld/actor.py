"""Actors are objects that can exist in the world."""
import asyncio

from .coords import Direction, adjacent
from .world import Collision


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
        client.sight.stop()
        if self.target:
            target = self.target
        else:
            from .world_gen import create_dark_world
            target = create_dark_world()
        obj.world = target

        def respawn():
            client.sight.restart()
            obj.client.handle_refresh()
            try:
                obj.spawn(target, pos=(0, 0), effect='teleport')
            except Collision:
                obj.spawn(target, effect='teleport')
            print(f'{self.name} moved to {target}')
        loop = asyncio.get_event_loop()
        loop.call_later(0.5, respawn)

    def on_exit(self, obj):
        print(f'{self.name} left by {obj.name}')
