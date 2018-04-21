import asyncio
from .coords import Direction
from .actor import NPC
from .asyncutils import start_coroutine
from .items import InsufficientItems


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


class Forager(NPC):
    skin = 'man'
    title = 'Forager'

    @start_coroutine
    async def on_act(self, pc):
        if pc.client.can('eat_shrooms'):
            pc.client.say(self.title, "That's all I know!")

        if not pc.client.can('start_forage'):
            pc.client.say(self.title, "Sure, I can teach you about foraging.")
            await asyncio.sleep(2)
            try:
                pc.client.inventory.take('shroom', 5)
            except InsufficientItems:
                pc.client.say(self.title, "Go get me 5 mushrooms.")
            else:
                pc.client.say(
                    self.title,
                    "I see you have some mushrooms already."
                )
                await asyncio.sleep(2)
                pc.client.say(
                    self.title,
                    "You can only eat these ones. Let's throw the others away."
                )
                pc.client.grant('eat_shrooms')


def spawn_npcs(world):
    """Spawn NPCs in the given world."""
    yield Woodsman().spawn(world, (-14, 3), Direction.EAST)
    yield Magician().spawn(world, pos=(-40, -44))
    yield Forager().spawn(world, pos=(-40, 6))
