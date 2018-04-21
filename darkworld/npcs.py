import asyncio
from .dialog import ShopDialog, BlacksmithDialog
from .coords import Direction
from .actor import NPC, Scenery, Large
from .asyncutils import start_coroutine
from .items import (
    InsufficientItems, Torch, Elixir, Axe, Compass, AdventurerSword
)


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
        else:
            await asyncio.sleep(0.5)
            pc.client.say(self.title, "I have some things for sale.")
            pc.client.show_dialog(ShopDialog({
                Torch: 10,
                Elixir: 50,
                Compass: 30,
            }))


class Magician(NPC):
    skin = 'womanAlternative'
    title = 'Magician'

    @start_coroutine
    async def on_act(self, pc):
        self.face(pc)
        await asyncio.sleep(0.5)
        pc.client.say(
            self.title,
            "The stone rings? They're powered by mushrooms!"
        )
        pc.client.grant('teleport')
        await asyncio.sleep(2)
        self.direction = Direction.NORTH
        self.move(self.pos)


class Forager(NPC):
    skin = 'man'
    title = 'Forager'

    buy_shrooms = [100, 50, 20, 10]

    @start_coroutine
    async def on_act(self, pc):
        self.face(pc)
        if pc.client.can('sell_shrooms'):
            have = pc.client.inventory.count('mushroom')
            for num in self.buy_shrooms:
                if have >= num:
                    break
            else:
                pc.client.say(
                    self.title,
                    "If you find any mushrooms, I'll buy them "
                    "for 1 \U0001F4B0 each!"
                )
                return
            pc.client.say(
                self.title,
                f"Great, I'll take {num} mushrooms. "
                f"That makes {num} \U0001F4B0!"
            )
            pc.client.inventory.take('mushroom', num)
            pc.client.gold += num
            return

        if pc.client.can('eat_shrooms'):
            pc.client.say(self.title, "That's all I know!")
            await asyncio.sleep(2)
            pc.client.say(
                self.title,
                "If you find any mushrooms, I'll buy them "
                "for 1 \U0001F4B0 each!"
            )
            pc.client.grant('sell_shrooms')
            return

        if not pc.client.can('start_forage'):
            pc.client.say(self.title, "Sure, I can teach you about foraging.")
            await asyncio.sleep(2)
            try:
                pc.client.inventory.take('mushroom', 5)
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


class Blacksmith(NPC):
    skin = 'man'
    title = 'Blacksmith'

    @start_coroutine
    async def on_act(self, pc):
        self.face(pc)
        await asyncio.sleep(0.5)
        pc.client.say(self.title, "Aye, I can sort ye out with some tools.")
        await asyncio.sleep(2)
        pc.client.say(self.title, "If ye have the metal.")
        pc.client.show_dialog(BlacksmithDialog({
            Axe: 10,
            AdventurerSword: 30,
        }))


def spawn_npcs(world):
    """Spawn NPCs in the given world.

    This is only called when generating a new world! To update this you need
    to delete world data.

    """
    yield Woodsman().spawn(world, (-14, 3), Direction.EAST)
    yield Magician().spawn(world, pos=(-40, -44))
    yield Forager().spawn(world, pos=(-20, 8))
    yield Blacksmith().spawn(world, (-28, -18), Direction.SOUTH)
    yield Scenery('anvil').spawn(world, (-28, -17))
    yield Large('house', size=(2, 2), scale=16).spawn(world, (-31, -19))
    yield Large('nature/stone_statue', size=(2, 2), scale=32).spawn(world, (-41, -47), Direction.SOUTH)
