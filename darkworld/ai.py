import asyncio
import random
from collections import defaultdict
import heapq

from .coords import (
    random_dir, Direction, adjacent, manhattan_distance, neighbours,
    direction_to
)
from .world import Collision
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

        all_targets = list(self.targets)
        for e, target in list(self.enemies.items()):
            if not e.alive:
                continue
            if target and target.alive:
                dist = manhattan_distance(e.pos, target.pos)
                if dist == 1:
                    e.face(target)
                    target.hit(random.randint(1, e.damage))
                elif dist > 7:
                    # Lost target
                    self.enemies[e] = None
                else:
                    if not getattr(e, '_path', None):
                        path = a_star_search(e.world, e.pos, target.pos)
                        e._path = path
                    step = e._path.pop()
                    d = direction_to(e.pos, step)
                    try:
                        e.move_step(d)
                    except Collision:
                        e._path = None
            elif random.random() < 0.2:
                # random walk
                e.move_step(random_dir())
            elif all_targets:
                t = random.choice(all_targets)
                if manhattan_distance(e.pos, t.pos) < 6:
                    self.enemies[e] = t
                    self.targets[t].add(e)


# Code below taken from Red Blob Games


class PriorityQueue:
    def __init__(self):
        self.elements = []

    def __bool__(self):
        return bool(self.elements)

    def put(self, item, priority):
        heapq.heappush(self.elements, (priority, item))

    def get(self):
        return heapq.heappop(self.elements)[1]


def reconstruct_path(came_from, start, goal):
    current = goal
    path = []
    while current != start:
        current = came_from[current]
        path.append(current)
    path.pop()
    return path


def a_star_search(world, start, goal):
    frontier = PriorityQueue()
    frontier.put(start, 0)
    came_from = {}
    cost_so_far = {}
    came_from[start] = None
    cost_so_far[start] = 0

    while frontier:
        current = frontier.get()

        if current == goal:
            break

        new_cost = cost_so_far[current] + 1
        for next in neighbours(current):
            if next != goal and world.get(next):
                continue
            if next not in cost_so_far or new_cost < cost_so_far[next]:
                cost_so_far[next] = new_cost
                priority = new_cost + manhattan_distance(goal, next)
                frontier.put(next, priority)
                came_from[next] = current

    return reconstruct_path(came_from, start, goal)
