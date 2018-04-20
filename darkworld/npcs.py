from .actor import NPC


class Woodsman(NPC):
    skin = 'man'
    title = 'Woodsman'

    def on_act(self, pc):
        self.face(pc)
        pc.client.say(self.title, 'Hello there!')
