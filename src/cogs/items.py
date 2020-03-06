"""This is a cog for a discord.py bot.
It will add some dice rolling commands to a bot.
"""
#pylint: disable=E0402
import json
from difflib import SequenceMatcher
from discord.ext import commands
from discord import Embed


class Items(commands.Cog, name='Items'):
    def __init__(self, client):
        self.client = client
        with open('../state/items.json') as f:
            self.item_prices = json.load(f)

    def save_items(self):
        with open('../state/items.json', 'w') as f:
            json.dump(self.item_prices, f, indent=1)

    def find_items(self, query):
        matches = []
        for item in self.item_prices.keys():
            if query.lower() in item.lower():
                matches.append((2, item))
            else:
                ratio = SequenceMatcher(
                    None, item.lower(), query.lower()).ratio()
                if ratio >= 0.66:
                    matches.append((ratio, item))
        return [x[1] for x in sorted(matches, reverse=True)][:15]

    @commands.command(
        name='item',
        aliases=['i', 'price', 'p'],
    )
    async def get_items(self, ctx, *, item_query):
        """Search for the price of an item"""
        if not item_query:
            return
        matches = self.find_items(item_query)
        print(matches)
        if not matches:
            return
        description = [
            f'{item} - {self.item_prices[item]}' for item in matches]
        e = Embed(
            description='\n'.join(description)
        )
        await ctx.send(embed=e)

    @commands.command(
        name='itemadd',
        aliases=['ia', 'iadd'],
    )
    async def add_item(self, ctx, item_name: str, item_price: str):
        """Add/Overwrite an item to the item price-list

        Example:
        `!ia "Night Vision Goggles" "10 gp | 8 gp | 15 gp"`"""
        self.item_prices[item_name] = item_price
        self.save_items()
        await ctx.send(f'Item "{item_name}" added!')

    @commands.command(
        name='itemdelete',
        aliases=['id', 'idel'],
    )
    async def del_item(self, ctx, *, item_name: str):
        """Delete an item from the price-list

        Example:
        `!id Night Vision Goggles`"""
        if item_name in self.item_prices:
            del self.item_prices[item_name]
            self.save_items()
            await ctx.send(f'Item "{item_name}" deleted!')


def setup(client):
    client.add_cog(Items(client))
