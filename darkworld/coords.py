"""Coordinates and directions."""
import random
from enum import IntEnum
from collections import namedtuple


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


def adjacent(pos, direction):
    """Get the adjacent map coordinates in a particular direction."""
    dx, dy = DIRECTION_MAP[direction]
    x, y = pos
    return x + dx, y + dy


ALL_DIRECTIONS = list(Direction)


def random_dir():
    """Return a random direction."""
    return random.choice(ALL_DIRECTIONS)


def manhattan_distance(p1, p2):
    """Calculate the Manhattan distance between two points."""
    p1x, p1y = p1
    p2x, p2y = p2
    return abs(p1x - p2x) + abs(p1y - p2y)
