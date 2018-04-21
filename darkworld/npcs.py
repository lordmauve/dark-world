import asyncio
from .coords import Direction
from .actor import NPC
from .asyncutils import start_coroutine


class Woodsman(NPC):
    skin = 'man'
    title = 'Woodsman'

    @start_coroutine
    async def on_act(self, pc):
        self.face(pc)
        pc.client.say(self.title, "Hello there!")
        if not pc.client.can('teleport'):
            await asyncio.sleep(0.5)
            pc.client.say(self.title, "Have you seen the magician yet?")
            await asyncio.sleep(1)
            pc.client.say(self.title, "Just follow this road to the left.")


class Magician(NPC):
    skin = 'womanAlternative'
    title = 'Magician'

    def on_act(self, pc):
        self.face(pc)
        pc.client.say(
            self.title,
            "The stone rings? They're powered by mushrooms!"
        )
        pc.client.grant('teleport')


def spawn_npcs(world):
    """Spawn NPCs in the given world."""
    yield Woodsman().spawn(world, (-14, 3), Direction.EAST)
    yield Magician().spawn(world, pos=(-40, -44))
