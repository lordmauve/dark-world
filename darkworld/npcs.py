from .coords import Direction
from .actor import NPC


class Woodsman(NPC):
    skin = 'man'
    title = 'Woodsman'

    def on_act(self, pc):
        self.face(pc)
        pc.client.say(self.title, "Hello there!")
        pc.client.say(self.title, "Have you seen the magician yet?")
        pc.client.say(self.title, "Just follow this road left")


class Magician(NPC):
    skin = 'womanAlternative'
    title = 'Magician'

    def on_act(self, pc):
        self.face(pc)
        pc.client.say(self.title, 'Hello there!')


def spawn_npcs(world):
    """Spawn NPCs in the given world."""
    yield Woodsman().spawn(world, (-14, 3), Direction.EAST)
    yield Magician().spawn(world, pos=(-40, -44))
