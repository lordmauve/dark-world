import asyncio
import random
from collections import defaultdict

from .coords import random_dir, Direction, adjacent, manhattan_distance
from .actor import PC, Enemy

loop = asyncio.get_event_loop()


class All:
    """Allow subscribing to all events in a world."""
    def __contains__(self, p):
        return True


class EnemyAI:
    """An AI for a group of enemies."""

    def __init__(self, enemies=[]):
        self.enemies = {e: None for e in enemies}
        self.targets = defaultdict(set)
        self.rect = All()

    def moved(self, obj, from_pos, to_pos):
        if isinstance(obj, PC):
            self.check_adj(obj)

    def check_adj(self, obj):
        """Check whether the given object is adjacent to an enemy.

        If it is, target the object.

        """
        for d in Direction:
            pos = adjacent(obj.pos, d)
            o = obj.world.get(pos)
            if o is None:
                continue
            if o in self.enemies:
                self.enemies[o] = obj
                self.targets[obj].add(o)

    def updated(self, obj, effect):
        pass

    def spawned(self, obj, pos, effect):
        if isinstance(obj, Enemy):
            self.enemies.add(obj)

        if isinstance(obj, PC):
            if not self.targets:
                loop.call_later(3, self.think)
            self.targets[obj] = set()

    def killed(self, obj, pos, effect):
        self.enemies.pop(obj, None)

        for e in self.targets.pop(obj, ()):
            self.enemies[e] = None

    def think(self):
        if self.targets and self.enemies:
            loop.call_later(0.5, self.think)

        for e, target in list(self.enemies.items()):
            if not e.alive:
                continue
            if target and target.alive:
                if manhattan_distance(e.pos, target.pos) == 1:
                    e.face(target)
                    target.hit(random.randint(1, e.damage))
            elif random.random() < 0.2:
                # random walk
                e.move_step(random_dir())
