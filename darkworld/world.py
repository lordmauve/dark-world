import random
import weakref
import traceback

from .coords import Rect


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


