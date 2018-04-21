from .items import InsufficientItems

class ChooseDialog:
    title = "Choose"

    def __init__(self, choices):
        self.choices = choices

    def to_json(self):
        c = []
        for k, v in self.choices.items():
            c.append({'key': k, **self.choice_to_json(v)})
        return {
            'title': self.title,
            'type': 'choose',
            'choices': c,
        }

    def choice_to_json(self, choice):
        """Display a choice as JSON."""

    def get_choice(self, key):
        """Get a choice from the list of choices."""
        return self.choices[key]

    def on_response(self, client, value):
        """Handle a response value from the client."""
        try:
            choice = self.get_choice(value)
        except KeyError:
            client.error_message('Invalid selection')
        self.on_choose(client.actor, choice)

    def on_choose(self, pc, value):
        """Subclasses can implement this to deal with choice."""


class InventoryDialog(ChooseDialog):
    title = "Inventory"

    def __init__(self, inventory):
        self.inventory = inventory
        super().__init__({
            obj.singular: (obj, count)
            for obj, count in inventory
        })

    def choice_to_json(self, choice):
        obj, count = choice
        title = (
            f'{count} {obj.plural}'
            if count != 1
            else f'{count} {obj.singular}'
        )
        return {
            'img': obj.image,
            'title': title,
        }

    def get_choice(self, key):
        return self.choices[key][0]

    def on_choose(self, pc, choice):
        choice.on_use(pc)


class ShopDialog(ChooseDialog):
    title = "Buy"
    unit = "\U0001F4B0"

    def __init__(self, available):
        """Construct a dialog for buying items.

        'available' should be a mapping of item -> price.

        """
        self.available = available
        super().__init__({
            obj.singular: (obj, price)
            for obj, price in available.items()
        })

    def choice_to_json(self, choice):
        obj, price = choice
        return {
            'img': obj.image,
            'title': obj.singular,
            'subtitle': f"{price} {self.unit}",
        }

    def on_choose(self, pc, choice):
        obj, price = choice
        if pc.client.gold >= price:
            pc.client.gold -= price
            pc.client.inventory.add(obj.singular)
            pc.client.text_message(
                f'You bought a {obj.singular} for {price} {self.unit}.'
            )
        else:
            pc.client.text_message(f"You can't afford that.")


class BlacksmithDialog(ShopDialog):
    unit = 'iron'

    def on_choose(self, pc, choice):
        obj, price = choice
        try:
            pc.client.inventory.take(self.unit, price)
        except InsufficientItems as e:
            pc.client.text_message(f"You can't afford that. {e.args[0]}")
        else:
            pc.client.inventory.add(obj.singular)
            pc.client.text_message(
                f'You bought a {obj.singular} for {price} {self.unit}.'
            )
